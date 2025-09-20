import os
import json
import asyncio
from typing import Dict, Any, List, Set, Optional

import boto3
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text as sql_text

from db import engine, Base
import models as db_models
from sql_utils import is_safe_sql

# Optional tools
from app.tools.what_if import simulate_scenario, diff_runs

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def _model_id() -> Optional[str]:
    # Read model id dynamically so .env changes after import are picked up
    return os.getenv("BEDROCK_MODEL_ID")


router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    run_id: Optional[str] = None


def _schema_from_metadata() -> tuple[str, List[str], Dict[str, Set[str]]]:
    lines: List[str] = []
    allowed_tables: List[str] = []
    schema: Dict[str, Set[str]] = {}
    for table in Base.metadata.sorted_tables:
        cols = []
        col_names: Set[str] = set()
        for c in table.columns:
            typename = str(c.type)
            cols.append(f"{c.name} {typename}")
            col_names.add(c.name)
        allowed_tables.append(table.name)
        schema[table.name] = col_names
        lines.append(f"TABLE {table.name} (" + ", ".join(cols) + ")")
    return "\n".join(lines), allowed_tables, schema


def _bedrock_client():
    if not _model_id():
        return None
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


# Tool specs exposed to Bedrock
TOOLS = [
    {
        "toolSpec": {
            "name": "get_schema",
            "description": "Return DB schema text, allowed tables, and columns. Use this before writing SQL.",
            "inputSchema": {"json": {"type": "object", "properties": {}, "additionalProperties": False}},
        }
    },
    {
        "toolSpec": {
            "name": "get_latest_run_id",
            "description": "Return the most recent run_id (by created_at).",
            "inputSchema": {"json": {"type": "object", "properties": {}, "additionalProperties": False}},
        }
    },
    {
        "toolSpec": {
            "name": "run_sql",
            "description": "Execute a read-only SQL SELECT with LIMIT<=200 and return rows. The SQL must include a WHERE run_id filter when relevant.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "A single safe SELECT statement with LIMIT<=200. No semicolon.",
                        }
                    },
                    "required": ["sql"],
                    "additionalProperties": False,
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "simulate_scenario",
            "description": "Clone a baseline run and apply demand multipliers and material caps; recompute plans and orders.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "baseline_run_id": {"type": ["string", "null"]},
                        "demand_multipliers": {"type": ["object", "null"]},
                        "material_caps": {"type": ["object", "null"]},
                    },
                    "additionalProperties": False,
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "diff_runs",
            "description": "Compare two runs and return deltas across forecast, production, and material orders.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "base_run_id": {"type": "string"},
                        "scenario_run_id": {"type": "string"},
                    },
                    "required": ["base_run_id", "scenario_run_id"],
                    "additionalProperties": False,
                }
            },
        }
    },
]


async def _handle_tool_call(name: str, args: dict):
    if name == "get_schema":
        schema_text, allowed_tables, schema_map = _schema_from_metadata()
        return {
            "schema_text": schema_text,
            "allowed_tables": allowed_tables,
            "schema_map": {k: list(v) for k, v in schema_map.items()},
        }

    if name == "get_latest_run_id":
        from sqlalchemy import select, desc
        try:
            with engine.connect() as conn:
                stmt = select(db_models.Run.id).order_by(desc(db_models.Run.created_at)).limit(1)
                res = conn.execute(stmt)
                row = res.first()
                return {"run_id": row[0] if row else None}
        except Exception as e:
            return {"error": f"Failed to get latest run_id: {e}"}

    if name == "run_sql":
        sql_query = (args.get("sql") or "").strip()
        schema_text, allowed_tables, schema_map = _schema_from_metadata()
        if not is_safe_sql(sql_query, allowed_tables, schema_map):
            return {"error": "SQL failed safety checks", "sql": sql_query}
        rows = []
        try:
            with engine.connect() as conn:
                result = conn.execute(sql_text(sql_query))
                for r in result:
                    rows.append(dict(r._mapping))
        except Exception as e:
            return {"error": f"SQL execution error: {e}", "sql": sql_query}
        return {"rows": rows}

    if name == "simulate_scenario":
        return simulate_scenario(args or {})

    if name == "diff_runs":
        return diff_runs(args or {})

    return {"error": f"Unknown tool: {name}"}


@router.post("")
async def chat(req: ChatRequest):
    schema_text, allowed_tables, schema_map = _schema_from_metadata()

    async def gen():
        # Send an early tiny chunk to nudge proxies/browsers to display streaming
        yield " "
        await asyncio.sleep(0.05)

        # Resolve run_id if missing
        run_id = req.run_id
        if not run_id:
            latest = await _handle_tool_call("get_latest_run_id", {})
            run_id = latest.get("run_id")

        br = _bedrock_client()
        if br is None:
            yield "Bedrock not configured. Please set BEDROCK_MODEL_ID."
            return

        # Generate SQL query with Bedrock
        system_prompt = (
            "Convert the user’s question into a SINGLE safe SQL SELECT query against the schema below. "
            "Rules: only SELECT, must include LIMIT 200, no insert/update/delete, no pragma, no multiple statements, no semicolons."
        )
        user_prompt = (
            f"User question: {req.question}\n"
            + (f"Run context: Only include rows where run_id = '{run_id}' when relevant.\n" if run_id else "")
            + f"Schema:\n{schema_text}\nReturn only the SQL query."
        )

        def _clean_sql(s: str) -> str:
            s = s.strip()
            if s.startswith("```"):
                parts = s.split("\n")[1:]
                if parts and parts[-1].strip().startswith("```"):
                    parts = parts[:-1]
                s = "\n".join(parts).strip()
            if s.endswith(";"):
                s = s[:-1].strip()
            return s

        try:
            payload = {
                "modelId": _model_id(),
                "system": [{"text": system_prompt}],
                "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
                "inferenceConfig": {"maxTokens": 400, "temperature": 0.0, "topP": 1.0},
            }
            resp = br.converse(**payload)
            content = resp.get("output", {}).get("message", {}).get("content", [])
            text_parts = [p.get("text", "") for p in content if "text" in p]
            sql_query = _clean_sql("".join(text_parts))
        except Exception as e:
            yield f"Error generating SQL: {e}"
            return

        if not is_safe_sql(sql_query, allowed_tables, schema_map):
            yield "I couldn't generate a safe SQL query."
            return

        # Run SQL
        rows: List[Dict[str, Any]] = []
        try:
            with engine.connect() as conn:
                result = conn.execute(sql_text(sql_query))
                for r in result:
                    rows.append(dict(r._mapping))
        except Exception as e:
            yield f"SQL execution error: {e}"
            return

        # Explain with streaming
        explain_user = (
            "Explain these results in plain English for a supply chain planner. Be concise and clear.\n"
            + json.dumps(rows)[:6000]
        )
        try:
            async for chunk in _stream_bedrock_explanation(br, model_id=_model_id(), explain_text=explain_user):
                yield chunk
        except Exception as e:
            yield f"Streaming failed: {e}"

    return StreamingResponse(
        gen(),
        media_type="text/plain; charset=utf-8",
        headers={
            # Disable proxy buffering (nginx), encourage immediate flush
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    try:
        init = await ws.receive_json()
        question: str = init.get("question")
        run_id: Optional[str] = init.get("run_id")
        if not question:
            await ws.send_text(json.dumps({"error": "question is required"}))
            await ws.close()
            return
        if not run_id:
            latest = await _handle_tool_call("get_latest_run_id", {})
            run_id = latest.get("run_id") or ""

        system_prompt = (
            "You are Food Copilot. Answer user questions by using tools to get DB schema and query the DB. "
            "Rules: Generate only SELECT queries, include LIMIT 200, avoid semicolons, and filter by run_id when relevant. "
            "If run_id is missing, call get_latest_run_id. If schema is unknown, call get_schema before writing SQL. "
            "You can also run what-if simulations with simulate_scenario and compare runs with diff_runs."
        )

        br = _bedrock_client()
        if br is None:
            await ws.send_text("Bedrock not configured.")
            await ws.close()
            return

        messages = [{"role": "user", "content": [{"text": f"Question: {question}\nRunId: {run_id}"}]}]

        for _ in range(6):
            payload = {
                "modelId": _model_id(),
                "system": [{"text": system_prompt}],
                "messages": messages,
                "inferenceConfig": {"maxTokens": 700, "temperature": 0.0},
                "toolConfig": {"tools": TOOLS, "toolChoice": {"auto": {}}},
            }
            resp = br.converse(**payload)
            content = resp.get("output", {}).get("message", {}).get("content", [])

            tool_calls = [c.get("toolUse") for c in content if c.get("toolUse")]
            text_parts = [c.get("text") for c in content if "text" in c]

            if not tool_calls:
                for token in ("".join(text_parts)).split():
                    await ws.send_text(token + " ")
                await ws.send_text("\n[END]")
                await ws.close()
                return

            tool_results_content = []
            for tu in tool_calls:
                name = tu.get("name")
                args = tu.get("input", {}) or {}
                result = await _handle_tool_call(name, args)
                tool_results_content.append({
                    "toolResult": {"toolUseId": tu.get("toolUseId"), "content": [{"json": result}]}
                })

            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": tool_results_content})

    except WebSocketDisconnect:
        return
    except Exception as e:
        await ws.send_text(json.dumps({"error": str(e)}))
        await ws.close()


# Streaming helpers
async def _stream_bedrock_explanation(br, model_id: Optional[str], explain_text: str):
    if not model_id:
        raise RuntimeError("BEDROCK_MODEL_ID is not set")
    payload = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": explain_text}]}],
        "inferenceConfig": {"maxTokens": 600, "temperature": 0.2, "topP": 0.9},
    }
    try:
        resp = br.converse_stream(**payload)
        stream = resp.get("stream")
    except Exception:
        stream = None

    if stream:
        for event in stream:
            delta_evt = event.get("contentBlockDelta")
            if delta_evt and isinstance(delta_evt, dict):
                delta = delta_evt.get("delta", {})
                text = (delta or {}).get("text")
                if text:
                    yield text
                    # yield control to event loop to flush chunk
                    await asyncio.sleep(0.02)
            stop_evt = event.get("messageStop")
            if stop_evt is not None:
                break
        return

    # Fallback: non-streaming response, chunk manually
    resp2 = br.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": explain_text}]}],
        inferenceConfig={"maxTokens": 600, "temperature": 0.2, "topP": 0.9},
    )
    content = resp2.get("output", {}).get("message", {}).get("content", [])
    text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
    full_text = "".join(text_parts)
    # Emit in small chunks so clients can render progressively
    chunk_size = 128
    for i in range(0, len(full_text), chunk_size):
        yield full_text[i:i+chunk_size]
        await asyncio.sleep(0.04)
