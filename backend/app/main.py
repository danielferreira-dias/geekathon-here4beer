import os
import json
from typing import Dict, Any, List, Set

import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text as sql_text
from mangum import Mangum
from dotenv import load_dotenv

# Load environment variables from .env if present (for local/dev convenience)
load_dotenv()

from app.routers.analyze import router as analyze_router
from db import engine, Base
import models as db_models
from sql_utils import is_safe_sql

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")

app = FastAPI(title="food-copilot-backend", version="0.1.0")

# CORS (allow all by default; adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)


# Ensure database tables exist at startup (helps in local/dev if init_db wasn't run)
@app.on_event("startup")
async def _init_db_on_startup():
    # Models are imported above as db_models to register metadata
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    return {"status": "ok", "service": "food-copilot-backend"}


@app.get("/health")
async def health():
    """Basic health and AWS credentials status check.
    Returns service info, region, model id presence, and STS identity if available.
    Helps diagnose why Bedrock requests may fail (e.g., expired credentials).
    """
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    info: Dict[str, Any] = {
        "status": "ok",
        "service": "food-copilot-backend",
        "aws_region": AWS_REGION,
        "bedrock_model_id_present": bool(BEDROCK_MODEL_ID),
        "bedrock_model_id": BEDROCK_MODEL_ID if BEDROCK_MODEL_ID else None,
        "aws": {
            "credentials_present": bool(os.getenv("AWS_ACCESS_KEY_ID") and (os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SESSION_TOKEN"))),
            "access_key_id_prefix": (os.getenv("AWS_ACCESS_KEY_ID") or "")[:4],
            "session_token_present": bool(os.getenv("AWS_SESSION_TOKEN")),
            "expiry_time": None,
            "sts_identity": None,
            "error": None,
        },
    }

    try:
        session = boto3.session.Session(region_name=AWS_REGION)
        creds = session.get_credentials()
        if creds is not None and hasattr(creds, "get_frozen_credentials"):
            # Some providers expose expiry_time on the underlying credentials object
            expiry = getattr(creds, "expiry_time", None)
            if expiry is not None:
                try:
                    info["aws"]["expiry_time"] = expiry.isoformat() if hasattr(expiry, "isoformat") else str(expiry)
                except Exception:
                    info["aws"]["expiry_time"] = str(expiry)
        sts = session.client("sts")
        ident = sts.get_caller_identity()
        info["aws"]["sts_identity"] = {
            "account": ident.get("Account"),
            "arn": ident.get("Arn"),
            "user_id": ident.get("UserId"),
        }
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code") if hasattr(e, "response") else None
        info["aws"]["error"] = {"type": "ClientError", "code": code, "message": str(e)}
    except BotoCoreError as e:
        info["aws"]["error"] = {"type": "BotoCoreError", "message": str(e)}
    except Exception as e:
        info["aws"]["error"] = {"type": "Exception", "message": str(e)}

    return info


class ChatRequest(BaseModel):
    question: str
    run_id: str


def _schema_from_metadata() -> tuple[str, List[str], Dict[str, Set[str]]]:
    """Builds a human-readable schema string, list of allowed tables, and table->columns map."""
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
    if not BEDROCK_MODEL_ID:
        raise RuntimeError("BEDROCK_MODEL_ID is not set")
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


def _converse_with_retry(br, payload: dict):
    import botocore.exceptions as be

    def _call():
        return br.converse(**payload)

    try:
        return _call()
    except be.ClientError as e:
        code = getattr(e, 'response', {}).get('Error', {}).get('Code')
        if code in {"ExpiredToken", "ExpiredTokenException"}:
            # refresh client and retry
            session = boto3.session.Session(region_name=AWS_REGION)
            br2 = session.client("bedrock-runtime")
            return br2.converse(**payload)
        raise
    except be.BotoCoreError:
        # transient, retry once with a new client
        session = boto3.session.Session(region_name=AWS_REGION)
        br2 = session.client("bedrock-runtime")
        return br2.converse(**payload)


# Tool specifications for Bedrock Converse tool-use
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
                # models imported as db_models at top
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

    return {"error": f"Unknown tool: {name}"}


@app.post("/chat")
async def chat(req: ChatRequest):
    # Build schema
    schema_text, allowed_tables, schema_map = _schema_from_metadata()

    # Compose prompt for SQL generation
    system_prompt = (
        "Convert the user’s question into a SINGLE safe SQL SELECT query against the schema below. "
        "Rules: only SELECT, must include LIMIT 200, no insert/update/delete, no pragma, no multiple statements, no semicolons."
    )
    user_prompt = (
        "User question: "
        + req.question
        + "\nRun context: Only include rows where run_id = '"
        + req.run_id.replace("'", "''")
        + "' when relevant.\nSchema:\n"
        + schema_text
        + "\nReturn only the SQL query."
    )

    def _clean_sql(s: str) -> str:
        s = s.strip()
        if s.startswith("```"):
            parts = s.split("\n")
            if parts:
                parts = parts[1:]
            if parts and parts[-1].strip().startswith("```"):
                parts = parts[:-1]
            s = "\n".join(parts).strip()
        if s.endswith(";"):
            s = s[:-1].strip()
        return s

    sql_query: str
    try:
        br = _bedrock_client()
        payload = {
            "modelId": BEDROCK_MODEL_ID,
            "system": [{"text": system_prompt}],
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {"maxTokens": 400, "temperature": 0.0, "topP": 1.0},
        }
        resp = _converse_with_retry(br, payload)
        content = resp.get("output", {}).get("message", {}).get("content", [])
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and "text" in part]
        sql_query = _clean_sql("".join(text_parts))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bedrock error generating SQL: {e}")

    # Validate SQL; if fails, do a corrective retry with stricter instructions
    if not is_safe_sql(sql_query, allowed_tables, schema_map):
        try:
            br = _bedrock_client()
            allowed_tables_list = ", ".join(allowed_tables)
            retry_user = (
                "The following SQL was rejected by safety checks. Regenerate a SINGLE safe SELECT query that conforms strictly to the rules.\n"
                f"Original question: {req.question}\n"
                f"Original SQL: {sql_query}\n"
                f"Rules: only SELECT, include LIMIT 200, no semicolons, and only use these tables: {allowed_tables_list}.\n"
                "Use only columns that exist in the schema below. Always include run_id filter when appropriate.\n"
                "Schema:\n" + schema_text + "\nReturn only the SQL query."
            )
            payload = {
                "modelId": BEDROCK_MODEL_ID,
                "system": [{"text": system_prompt}],
                "messages": [{"role": "user", "content": [{"text": retry_user}]}],
                "inferenceConfig": {"maxTokens": 400, "temperature": 0.0, "topP": 1.0},
            }
            resp = _converse_with_retry(br, payload)
            content = resp.get("output", {}).get("message", {}).get("content", [])
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and "text" in part]
            sql_query = _clean_sql("".join(text_parts))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Bedrock error generating SQL on retry: {e}")

    # Final validation after potential retry
    if not is_safe_sql(sql_query, allowed_tables, schema_map):
        raise HTTPException(status_code=400, detail="Generated SQL failed safety checks")

    # Execute SQL (read-only)
    rows: List[Dict[str, Any]] = []
    try:
        with engine.connect() as conn:
            result = conn.execute(sql_text(sql_query))
            for r in result:
                rows.append(dict(r._mapping))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {e}")

    # Ask Bedrock to explain the results
    explanation = ""
    try:
        br = _bedrock_client()
        explain_user = (
            "Explain these results in plain English for a supply chain planner. Be concise and clear.\n"
            + json.dumps(rows)[:6000]
        )
        payload = {
            "modelId": BEDROCK_MODEL_ID,
            "messages": [{"role": "user", "content": [{"text": explain_user}]}],
            "inferenceConfig": {"maxTokens": 400, "temperature": 0.2, "topP": 0.9},
        }
        resp = _converse_with_retry(br, payload)
        content = resp.get("output", {}).get("message", {}).get("content", [])
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and "text" in part]
        explanation = ("".join(text_parts)).strip()
    except Exception:
        # Fallback simple explanation
        explanation = f"Returned {len(rows)} rows."

    return {"sql": sql_query, "rows": rows, "answer": explanation}


@app.post("/chat2")
async def chat2(req: ChatRequest):
    """Tool-use powered chat that lets the model fetch schema, pick latest run_id, run SQL, and answer."""
    system_prompt = (
        "You are Food Copilot. Answer user questions by using tools to get DB schema and query the DB. "
        "Rules: Generate only SELECT queries, include LIMIT 200, avoid semicolons, and filter by run_id when relevant. "
        "If run_id is missing, call get_latest_run_id. If schema is unknown, call get_schema before writing SQL. "
        "Prefer returning a short explanation plus key rows."
    )

    br = _bedrock_client()

    # Seed conversation with the user's question and optional run_id
    messages = [
        {"role": "user", "content": [{"text": f"Question: {req.question}\nRunId: {req.run_id or ''}"}]}
    ]

    # Up to 4 tool-use rounds
    for _ in range(4):
        payload = {
            "modelId": BEDROCK_MODEL_ID,
            "system": [{"text": system_prompt}],
            "messages": messages,
            "inferenceConfig": {"maxTokens": 700, "temperature": 0.0},
            "toolConfig": {"tools": TOOLS, "toolChoice": {"auto": {}}},
        }
        try:
            resp = _converse_with_retry(br, payload)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Bedrock error during tool-use: {e}")

        content = resp.get("output", {}).get("message", {}).get("content", [])

        # Gather any toolUse calls from the assistant
        tool_calls = []
        for c in content:
            if isinstance(c, dict) and c.get("toolUse"):
                tool_calls.append(c.get("toolUse"))

        if not tool_calls:
            # No tool calls -> final answer
            text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and "text" in c]
            final_text = ("".join(text_parts)).strip()
            return {"answer": final_text}

        # Execute each tool call
        tool_results_content = []
        for tu in tool_calls:
            name = tu.get("name")
            args = tu.get("input", {}) or {}
            result = await _handle_tool_call(name, args)
            tool_results_content.append({
                "toolResult": {
                    "toolUseId": tu.get("toolUseId"),
                    "content": [{"json": result}],
                }
            })

        # Append assistant's toolUse messages and user-supplied tool results
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": tool_results_content})

    return {"answer": "I couldn’t complete the task within the tool-use steps. Please try again."}


# AWS Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
