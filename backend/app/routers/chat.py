import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Set, Optional
from collections import OrderedDict, deque

import boto3
import requests
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
AGENT_SERVICE_BASE = "http://ec2-34-229-83-157.compute-1.amazonaws.com"
AGENT_SERVICE_QUERY_URL = f"{AGENT_SERVICE_BASE}/query"


def _model_id() -> Optional[str]:
    # Read model id dynamically so .env changes after import are picked up
    return os.getenv("BEDROCK_MODEL_ID")


logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


# ---- Lightweight in-memory conversation history ----
class ConversationMemory:
    def __init__(self, max_conversations: int = 200, max_turns: int = 12):
        self.max_conversations = max_conversations
        self.max_turns = max_turns
        self._store: OrderedDict[str, deque] = OrderedDict()

    def get(self, conv_id: Optional[str]) -> List[Dict[str, Any]]:
        if not conv_id:
            return []
        if conv_id in self._store:
            # move to end (LRU)
            self._store.move_to_end(conv_id)
            return list(self._store[conv_id])
        return []

    def append(self, conv_id: Optional[str], role: str, text: str) -> None:
        if not conv_id:
            return
        dq = self._store.get(conv_id)
        if dq is None:
            dq = deque(maxlen=self.max_turns * 2)  # user+assistant per turn
            self._store[conv_id] = dq
        dq.append({"role": role, "content": [{"text": text}]})
        # Enforce LRU size
        while len(self._store) > self.max_conversations:
            self._store.popitem(last=False)

    def clear(self, conv_id: Optional[str]) -> None:
        if conv_id and conv_id in self._store:
            del self._store[conv_id]


_memory = ConversationMemory()


class ChatRequest(BaseModel):
    question: str
    run_id: Optional[str] = None
    conversation_id: Optional[str] = None


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
    {
        "toolSpec": {
            "name": "agent_service_query",
            "description": "Call external agent-service to fetch provider info or other procurement assistance. Provide a natural language 'message'.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Natural language question for the procurement agent."}
                    },
                    "required": ["message"],
                    "additionalProperties": False
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "find_providers_for_product",
            "description": "Convenience wrapper to ask the procurement agent which providers produce/sell a given product (SKU).",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "product": {"type": "string", "description": "Product or SKU name, e.g., 'milk'"}
                    },
                    "required": ["product"],
                    "additionalProperties": False
                }
            }
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

    if name == "agent_service_query":
        message = (args or {}).get("message") or ""
        payload = {"message": message}
        try:
            logger.info("[AgentServiceTool] Calling %s with payload=%s", AGENT_SERVICE_QUERY_URL, payload)
            r = requests.post(AGENT_SERVICE_QUERY_URL, json=payload, timeout=10)
            text = r.text
            try:
                data = r.json()
            except Exception:
                data = {"response": text}
            logger.info("[AgentServiceTool] Status=%s Response=%s", r.status_code, data)
            return {"response": data.get("response")}
        except Exception as e:
            logger.exception("[AgentServiceTool] ERROR calling service: %s", e)
            return {"error": f"agent_service_query failed: {e}"}

    if name == "find_providers_for_product":
        product = ((args or {}).get("product") or "").strip()
        message = f"what providers produce {product}?" if product else "what providers produce ?"
        payload = {"message": message}
        try:
            logger.info("[AgentServiceTool] Calling %s with payload=%s", AGENT_SERVICE_QUERY_URL, payload)
            r = requests.post(AGENT_SERVICE_QUERY_URL, json=payload, timeout=10)
            text = r.text
            try:
                data = r.json()
            except Exception:
                data = {"response": text}
            logger.info("[AgentServiceTool] Status=%s Response=%s", r.status_code, data)
            return {"response": data.get("response"), "product": product}
        except Exception as e:
            logger.exception("[AgentServiceTool] ERROR calling service: %s", e)
            return {"error": f"find_providers_for_product failed: {e}", "product": product}

    return {"error": f"Unknown tool: {name}"}


@router.post("")
async def chat(req: ChatRequest):
    schema_text, allowed_tables, schema_map = _schema_from_metadata()

    async def gen():
        # Send an early tiny chunk to nudge proxies/browsers to display streaming
        yield " "
        await asyncio.sleep(0.05)

        try:
            logger.info("[POST /chat] Received question. conversation_id=%s run_id=%s question=%s", req.conversation_id, req.run_id, (req.question or "")[:200])
        except Exception:
            pass

        # Resolve run_id if missing
        run_id = req.run_id
        if not run_id:
            latest = await _handle_tool_call("get_latest_run_id", {})
            run_id = latest.get("run_id")
        try:
            logger.info("[POST /chat] Using run_id=%s", run_id)
        except Exception:
            pass

        # Fallback: handle "low SKUs" style questions directly via DB without Bedrock
        q_lower = (req.question or "").lower()
        low_keywords = ["low", "low stock", "running low", "replenish", "reorder"]
        sku_keywords = ["sku", "skus", "product", "products", "inventory", "stock", "stocks", "stock level", "stock levels", "stockout", "stock-outs", "stock outs"]
        if any(k in q_lower for k in low_keywords) and any(k in q_lower for k in sku_keywords):
            try:
                with engine.connect() as conn:
                    sql = """
                    SELECT sku, forecasted_demand, current_inventory, suggested_production
                    FROM production_plans
                    WHERE 1=1
                    """
                    params = {}
                    if run_id:
                        sql += " AND run_id = :run_id"
                        params["run_id"] = run_id
                    sql += " AND CAST(current_inventory AS INTEGER) < CAST(forecasted_demand AS INTEGER)"
                    sql += " LIMIT 200"
                    result = conn.execute(sql_text(sql), params)
                    rows = [dict(r._mapping) for r in result]
                # Format a concise response
                if not rows:
                    msg = "No SKUs are currently below forecasted demand in the latest run."
                    try:
                        logger.info("[POST /chat] Fallback low-SKUs: no rows found")
                    except Exception:
                        pass
                    yield msg
                    # Save to convo memory
                    try:
                        if req.conversation_id:
                            _memory.append(req.conversation_id, "user", req.question)
                            _memory.append(req.conversation_id, "assistant", msg)
                    except Exception:
                        pass
                    return
                # Prepare list and base lines
                items = []
                lines = ["SKUs running low (inventory < forecast):"]
                for r in rows[:50]:
                    sku = r.get('sku')
                    try:
                        fd = int(r.get("forecasted_demand", 0))
                    except Exception:
                        fd = r.get("forecasted_demand")
                    try:
                        ci = int(r.get("current_inventory", 0))
                    except Exception:
                        ci = r.get("current_inventory")
                    try:
                        sp = int(r.get("suggested_production", 0))
                    except Exception:
                        sp = r.get("suggested_production")
                    # Compute deficit if possible
                    deficit = None
                    try:
                        deficit = int(fd) - int(ci)
                    except Exception:
                        pass
                    items.append({"sku": sku, "fd": fd, "ci": ci, "sp": sp, "deficit": deficit})
                    if deficit is not None:
                        lines.append(f"- {sku}: inv {ci}, forecast {fd}, deficit {deficit}, suggested_production {sp}")
                    else:
                        lines.append(f"- {sku}: inv {ci}, forecast {fd}, suggested_production {sp}")

                # Auto-contact external procurement agent for a few top-low SKUs
                providers_sections: List[str] = []
                try:
                    # Pick up to 4 most critical (largest deficit) items with a valid SKU string
                    top_items = [it for it in items if isinstance(it.get('sku'), str)]
                    top_items = [it for it in top_items if it.get('deficit') is not None]
                    top_items.sort(key=lambda x: int(x.get('deficit', 0)), reverse=True)
                    top_items = top_items[:4]

                    if top_items:
                        logger.info("[POST /chat] Auto-procurement: querying providers for %d SKUs", len(top_items))
                        tasks = []
                        for it in top_items:
                            sku = it['sku']
                            # Log tool usage explicitly
                            logger.info("[POST /chat] Tool(find_providers_for_product) args={product=%s}", sku)
                            tasks.append(_handle_tool_call("find_providers_for_product", {"product": sku}))
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for it, res in zip(top_items, results):
                            sku = it['sku']
                            if isinstance(res, Exception):
                                logger.exception("[POST /chat] Provider query failed for %s: %s", sku, res)
                                continue
                            if not isinstance(res, dict):
                                continue
                            resp_text = (res.get("response") or "").strip()
                            if not resp_text:
                                continue
                            # Skip "No providers found" responses
                            if resp_text.lower().startswith("no providers found"):
                                continue
                            # Include as-is; external response already formatted
                            providers_sections.append(resp_text)
                except Exception as e:
                    logger.exception("[POST /chat] Auto-procurement section failed: %s", e)

                # Combine final text
                if providers_sections:
                    lines.append("")
                    lines.append("Potential suppliers (auto-fetched):")
                    for sec in providers_sections:
                        lines.append(sec)
                text = "\n".join(lines)
                try:
                    logger.info("[POST /chat] Fallback low-SKUs response generated without Bedrock. rows=%d providers=%d", len(rows), len(providers_sections))
                except Exception:
                    pass
                yield text
                # Save this turn
                try:
                    if req.conversation_id:
                        _memory.append(req.conversation_id, "user", req.question)
                        _memory.append(req.conversation_id, "assistant", text)
                except Exception:
                    pass
                return
            except Exception as e:
                # If fallback fails, continue to Bedrock path
                try:
                    logger.exception("[POST /chat] Low-SKUs fallback failed: %s", e)
                except Exception:
                    pass

        # Supplier/provider intent: directly ask external procurement agent
        q_lower = (req.question or "").lower().strip()
        supplier_keywords = [
            "recommend a supplier",
            "recommend supplier",
            "supplier for",
            "provider for",
            "recommend a provider",
            "find supplier",
            "find providers",
            "find a supplier",
            "recommend vendor",
            "vendor for",
            "where to buy",
            "purchase from",
        ]
        if any(k in q_lower for k in supplier_keywords):
            # Naive product extraction: substring after ' for ' if present; else last token
            product_raw = None
            try:
                if " for " in q_lower:
                    # Use original casing from question for product span
                    after_for = (req.question or "").split(" for ", 1)[1]
                    product_raw = after_for.strip().strip("?.! ")
                else:
                    # fallback: last word
                    parts_orig = (req.question or "").strip().strip("?.! ").split()
                    product_raw = parts_orig[-1] if parts_orig else None
            except Exception:
                product_raw = None
            product = (product_raw or "").strip()
            if product:
                try:
                    logger.info("[POST /chat] Tool(find_providers_for_product) args={product=%s}", product)
                except Exception:
                    pass
                res = await _handle_tool_call("find_providers_for_product", {"product": product})
                # Build final text from tool response
                resp_text = ""
                if isinstance(res, dict):
                    resp_text = (res.get("response") or "").strip()
                if not resp_text:
                    msg = f"I couldn't retrieve supplier information for '{product}' right now."
                else:
                    msg = resp_text
                try:
                    if req.conversation_id:
                        _memory.append(req.conversation_id, "user", req.question)
                        _memory.append(req.conversation_id, "assistant", msg)
                except Exception:
                    pass
                yield msg
                return
            else:
                # No product parsed; fall through to Bedrock
                try:
                    logger.info("[POST /chat] Supplier intent detected but no product parsed; falling back to Bedrock")
                except Exception:
                    pass

        br = _bedrock_client()
        if br is None:
            try:
                logger.info("[POST /chat] Bedrock not configured; responding with guidance")
            except Exception:
                pass
            yield "Bedrock not configured. Please set BEDROCK_MODEL_ID."
            return

        # Prepare conversation history (natural language only)
        conv_id = req.conversation_id
        history_msgs = _memory.get(conv_id)

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
                "messages": [*history_msgs, {"role": "user", "content": [{"text": user_prompt}]}],
                "inferenceConfig": {"maxTokens": 400, "temperature": 0.0, "topP": 1.0},
            }
            resp = br.converse(**payload)
            content = resp.get("output", {}).get("message", {}).get("content", [])
            text_parts = [p.get("text", "") for p in content if "text" in p]
            sql_query = _clean_sql("".join(text_parts))
            try:
                logger.info("[POST /chat] Generated SQL (truncated): %s", sql_query[:200])
            except Exception:
                pass
        except Exception as e:
            try:
                logger.exception("[POST /chat] Error generating SQL: %s", e)
            except Exception:
                pass
            yield f"Error generating SQL: {e}"
            return

        if not is_safe_sql(sql_query, allowed_tables, schema_map):
            try:
                logger.info("[POST /chat] Generated SQL failed safety checks; refusing to execute.")
            except Exception:
                pass
            yield "I couldn't generate a safe SQL query."
            return

        # Run SQL
        rows: List[Dict[str, Any]] = []
        try:
            try:
                logger.info("[POST /chat] Executing SQL...")
            except Exception:
                pass
            with engine.connect() as conn:
                result = conn.execute(sql_text(sql_query))
                for r in result:
                    rows.append(dict(r._mapping))
            try:
                logger.info("[POST /chat] SQL executed. rows=%d", len(rows))
            except Exception:
                pass
        except Exception as e:
            try:
                logger.exception("[POST /chat] SQL execution error: %s", e)
            except Exception:
                pass
            yield f"SQL execution error: {e}"
            return

        # Explain with streaming (do not store rows in memory)
        explain_user = (
            "Explain these results in plain English for a supply chain planner. Be concise and clear. "
            "You may rely on the prior conversation for context if relevant.\n\n"
            f"User question (may be a follow-up): {req.question}\n\n"
            + json.dumps(rows)[:6000]
        )
        assistant_chunks: List[str] = []
        try:
            try:
                logger.info("[POST /chat] Starting streaming explanation...")
            except Exception:
                pass
            async for chunk in _stream_bedrock_explanation(
                br,
                model_id=_model_id(),
                explain_text=explain_user,
                history_msgs=history_msgs,
            ):
                assistant_chunks.append(chunk)
                yield chunk
            try:
                logger.info("[POST /chat] Streaming explanation completed. total_chunks=%d", len(assistant_chunks))
            except Exception:
                pass
        except Exception as e:
            try:
                logger.exception("[POST /chat] Streaming failed: %s", e)
            except Exception:
                pass
            yield f"Streaming failed: {e}"
            return
        # Save this turn to memory (question + assistant explanation)
        try:
            if conv_id:
                _memory.append(conv_id, "user", req.question)
                final_text = "".join(assistant_chunks)
                _memory.append(conv_id, "assistant", final_text)
        except Exception:
            # Never fail the request due to memory bookkeeping
            pass

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
        conv_id: Optional[str] = init.get("conversation_id")
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
            "You can also run what-if simulations with simulate_scenario and compare runs with diff_runs. "
            "If you identify SKUs/products with low stock or that require replenishment, call find_providers_for_product (preferred) or agent_service_query to ask another agent for suppliers. "
            "In your final answer, include any provider list returned. If the tool response says 'No providers found', do not mention providers at all."
        )

        br = _bedrock_client()
        if br is None:
            await ws.send_text("Bedrock not configured.")
            await ws.close()
            return

        # Seed with prior conversation history if provided
        history_msgs = _memory.get(conv_id)
        messages = [*history_msgs, {"role": "user", "content": [{"text": f"Question: {question}\nRunId: {run_id}"}]}]

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
                final_text = "".join([t for t in text_parts if t])
                # Stream tokens to client
                for token in final_text.split():
                    await ws.send_text(token + " ")
                await ws.send_text("\n[END]")
                # Persist this turn
                try:
                    if conv_id:
                        _memory.append(conv_id, "user", question)
                        _memory.append(conv_id, "assistant", final_text)
                except Exception:
                    pass
                await ws.close()
                return

            tool_results_content = []
            for tu in tool_calls:
                name = tu.get("name")
                args = tu.get("input", {}) or {}
                try:
                    logger.info("[ToolCall] name=%s args=%s", name, args)
                except Exception:
                    pass
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
async def _stream_bedrock_explanation(br, model_id: Optional[str], explain_text: str, history_msgs: Optional[List[Dict[str, Any]]] = None):
    if not model_id:
        raise RuntimeError("BEDROCK_MODEL_ID is not set")
    msgs = []
    if history_msgs:
        msgs.extend(history_msgs)
    msgs.append({"role": "user", "content": [{"text": explain_text}]})
    payload = {
        "modelId": model_id,
        "messages": msgs,
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
    # Build messages with history for fallback as well
    msgs2 = []
    if history_msgs:
        msgs2.extend(history_msgs)
    msgs2.append({"role": "user", "content": [{"text": explain_text}]})
    resp2 = br.converse(
        modelId=model_id,
        messages=msgs2,
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
