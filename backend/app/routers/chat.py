import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Set, Optional
from collections import OrderedDict, deque
import re

import boto3
import requests
from fastapi import APIRouter
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


    return {"error": f"Unknown tool: {name}"}


def _summarize_agent_response(resp_text: str, limit_per_sku: int = 3) -> str:
    """Summarize the external procurement agent response into concise, context-aware bullets.
    Expected format segments like:
      Providers selling 'bread_loaf':
      - Root Vegetable Co: $2.99 - North Carolina (Stock: 400, Distance: 12km)
    If sections are not present, fall back to first few bullet lines.
    """
    if not resp_text:
        return ""
    lines = resp_text.splitlines()
    sections: Dict[str, List[Dict[str, Any]]] = {}
    current_sku: Optional[str] = None

    header_re = re.compile(r"^\s*providers selling ['\"]?([^'\"]+)['\"]?:\s*$", re.IGNORECASE)
    price_re = re.compile(r"\$(\d+(?:\.\d+)?)")
    stock_re = re.compile(r"stock:\s*(\d+)", re.IGNORECASE)
    dist_re = re.compile(r"distance:\s*(\d+)\s*km", re.IGNORECASE)

    for raw in lines:
        m = header_re.match(raw.strip())
        if m:
            current_sku = m.group(1).strip()
            sections.setdefault(current_sku, [])
            continue
        if raw.strip().startswith("- "):
            # Attempt to parse a provider bullet
            name = None
            price: Optional[float] = None
            stock: Optional[int] = None
            distance_km: Optional[int] = None
            content = raw.strip()[2:]
            # Name is text before first ':' if exists
            if ':' in content:
                name = content.split(':', 1)[0].strip()
            else:
                # fallback: until first ' - '
                name = content.split(' - ', 1)[0].strip()
            pm = price_re.search(raw)
            if pm:
                try:
                    price = float(pm.group(1))
                except Exception:
                    price = None
            sm = stock_re.search(raw)
            if sm:
                try:
                    stock = int(sm.group(1))
                except Exception:
                    stock = None
            dm = dist_re.search(raw)
            if dm:
                try:
                    distance_km = int(dm.group(1))
                except Exception:
                    distance_km = None
            entry = {"name": name, "price": price, "stock": stock, "distance_km": distance_km, "raw": raw.strip()}
            if current_sku:
                sections.setdefault(current_sku, [])
                sections[current_sku].append(entry)
            else:
                sections.setdefault("__unscoped__", [])
                sections["__unscoped__"].append(entry)
        else:
            # Non-bullet; ignore
            continue

    out: List[str] = []
    # Prefer sectioned output
    section_keys = [k for k in sections.keys() if k != "__unscoped__"]
    if section_keys:
        out.append("Supplier suggestions (top options):")
        for sku in section_keys:
            providers = sections.get(sku, [])
            # Keep first limit_per_sku already in order
            providers = providers[:limit_per_sku]
            if not providers:
                continue
            parts = []
            best_price = None
            best_name = None
            for p in providers:
                frag_parts = [p.get("name") or "Unknown"]
                if p.get("price") is not None:
                    frag_parts.append(f"${p['price']:.2f}")
                if p.get("stock") is not None:
                    frag_parts.append(f"stock {p['stock']}")
                if p.get("distance_km") is not None:
                    frag_parts.append(f"{p['distance_km']}km")
                parts.append(" ".join(part for part in frag_parts if part))
                # Track best price
                if p.get("price") is not None and (best_price is None or p['price'] < best_price):
                    best_price = p['price']
                    best_name = p.get("name")
            line = f"- {sku}: " + ", ".join(parts)
            if best_price is not None and best_name:
                line += f". Best price: {best_name} (${best_price:.2f})"
            out.append(line)
        return "\n".join(out)

    # Fallback: no section headers found; use first few bullets overall
    bullets = sections.get("__unscoped__", [])
    if bullets:
        out.append("Top supplier options:")
        for p in bullets[:limit_per_sku]:
            # Use raw for robustness
            out.append(p.get("raw") or "")
        return "\n".join(out).strip()

    # Last resort: return trimmed original text
    return "\n".join(lines[: 8]).strip()


def _extract_best_suppliers_from_summary(text: str) -> Dict[str, Dict[str, Any]]:
    """Parse lines like "- sku: ... Best price: Name ($X.YY)" into a map {sku: {name, price}}."""
    best: Dict[str, Dict[str, Any]] = {}
    if not text:
        return best
    line_re = re.compile(r"^\-\s*([^:]+):.*?Best price:\s*([^\(]+)\s*\(\$(\d+(?:\.\d+)?)\)", re.IGNORECASE)
    for ln in text.splitlines():
        m = line_re.match(ln.strip())
        if m:
            sku = m.group(1).strip()
            name = m.group(2).strip()
            try:
                price = float(m.group(3))
            except Exception:
                price = None
            best[sku] = {"name": name, "price": price}
    return best


def _compose_natural_recommendation(items: List[Dict[str, Any]], best_map: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Create a short, natural closing recommendation based on deficits and best suppliers."""
    prioritized = [it for it in items if isinstance(it.get("deficit"), int) and isinstance(it.get("sku"), str)]
    if not prioritized:
        return None
    prioritized.sort(key=lambda x: x.get("deficit", 0), reverse=True)
    top_names = [it["sku"] for it in prioritized[:2]]
    # First sentence: prioritization
    if len(top_names) == 1:
        s1 = f"Recommendation: prioritize {top_names[0]} due to the highest deficit."
    else:
        s1 = f"Recommendation: prioritize {top_names[0]} and {top_names[1]} due to the highest deficits."
    # Second sentence: best suppliers and order targets
    picks = []
    for it in prioritized[:4]:  # keep concise
        sku = it["sku"]
        deficit = it.get("deficit")
        best = best_map.get(sku)
        if best and best.get("price") is not None:
            picks.append(f"{sku} → {best['name']} (${best['price']:.2f}, order ~{deficit})")
        else:
            picks.append(f"{sku} → order ~{deficit}")
    s2 = "Best-price picks and order targets: " + ", ".join(picks) + "."
    s3 = "If you confirm, I can draft purchase orders to cover the gaps."
    return "\n".join([s1, s2, s3])


async def _fetch_supplier_summary_for_skus(sku_list: List[str], limit_per_sku: int = 3) -> Optional[str]:
    """Call agent-service for the given SKUs and ensure per-SKU summarized output.
    If the combined response is ambiguous (not grouped per SKU) and there are multiple SKUs,
    fallback to querying each SKU individually and merging concise lines per SKU.
    """
    if not sku_list:
        return None

    # 1) Try combined query with explicit formatting instructions
    joined = " and ".join(sku_list)
    combined_msg = (
        f"what suppliers produce {joined}? "
        f"Please include sections titled exactly: Providers selling '{{SKU}}': for each product, "
        f"with up to {limit_per_sku} bullet items per section (name, price with $, stock, distance in km)."
    )
    res = await _handle_tool_call("agent_service_query", {"message": combined_msg})
    resp_text = (res or {}).get("response") if isinstance(res, dict) else None
    providers_text = _summarize_agent_response((resp_text or "").strip(), limit_per_sku=limit_per_sku) if resp_text else ""

    def _is_ambiguous(text: str) -> bool:
        if not text:
            return True
        # Ambiguous if it's generic top options without per-SKU lines
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return True
        if lines[0].lower().startswith("top supplier options:"):
            return True
        # Look for lines like "- sku: ..."
        has_per_sku = any(re.match(r"^-\s*[^:]+:\s", ln) for ln in lines)
        return not has_per_sku

    if len(sku_list) > 1 and _is_ambiguous(providers_text):
        # 2) Fallback: query per SKU and merge
        merged_lines: List[str] = ["Supplier suggestions (top options):"]
        for sku in sku_list:
            single_msg = (
                f"what suppliers produce {sku}? Please include a section titled exactly: Providers selling '{sku}': "
                f"and list at most {limit_per_sku} suppliers as bullets."
            )
            single_res = await _handle_tool_call("agent_service_query", {"message": single_msg})
            single_resp_text = (single_res or {}).get("response") if isinstance(single_res, dict) else None
            summarized = _summarize_agent_response((single_resp_text or "").strip(), limit_per_sku=limit_per_sku) if single_resp_text else ""
            # Extract the first per-SKU line ("- sku: ...")
            if summarized:
                for ln in summarized.splitlines():
                    if ln.strip().startswith(f"- {sku}:"):
                        merged_lines.append(ln)
                        break
        final_text = "\n".join(merged_lines) if len(merged_lines) > 1 else providers_text
        return final_text.strip()

    return providers_text.strip() if providers_text else None


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
                providers_text: Optional[str] = None
                selected_skus: List[str] = []
                try:
                    # Pick up to 4 most critical (largest deficit) items with a valid SKU string
                    top_items = [it for it in items if isinstance(it.get('sku'), str)]
                    top_items = [it for it in top_items if it.get('deficit') is not None]
                    top_items.sort(key=lambda x: int(x.get('deficit', 0)), reverse=True)
                    top_items = top_items[:4]

                    if top_items:
                        selected_skus = [it['sku'] for it in top_items]
                        try:
                            logger.info("[POST /chat] Auto-procurement: querying providers for SKUs=%s", selected_skus)
                        except Exception:
                            pass
                        providers_text = await _fetch_supplier_summary_for_skus(selected_skus, limit_per_sku=3)
                except Exception as e:
                    logger.exception("[POST /chat] Auto-procurement section failed: %s", e)

                # Combine final text
                if providers_text:
                    lines.append("")
                    # Add a natural connective instead of a hard-coded header
                    try:
                        if selected_skus:
                            if len(selected_skus) == 1:
                                intro = f"I looked up supplier options for {selected_skus[0]}:"
                            else:
                                intro = "I looked up supplier options for " + ", ".join(selected_skus[:-1]) + f" and {selected_skus[-1]}:"
                            lines.append(intro)
                    except Exception:
                        # If anything goes wrong, skip the intro silently
                        pass
                    lines.append(providers_text)
                    # Add a natural closing recommendation based on deficits and best suppliers
                    try:
                        best_map = _extract_best_suppliers_from_summary(providers_text)
                        rec = _compose_natural_recommendation(items, best_map)
                        if rec:
                            lines.append("")
                            lines.append(rec)
                    except Exception:
                        pass
                text = "\n".join(lines)
                try:
                    logger.info("[POST /chat] Fallback low-SKUs response generated without Bedrock. rows=%d providers_text=%s", len(rows), 'yes' if providers_text else 'no')
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
            "suppliers",
            "supplier",
            "provider for",
            "providers",
            "recommend a provider",
            "find supplier",
            "find suppliers",
            "find providers",
            "find a supplier",
            "recommend vendor",
            "vendor for",
            "vendor",
            "vendors",
            "producer",
            "producers",
            "produce",
            "where to buy",
            "where can i buy",
            "who sells",
            "who supplies",
            "who produces",
            "purchase from",
            "buy",
            "purchase",
        ]
        if any(k in q_lower for k in supplier_keywords):
            # Forward the full natural-language question to the external procurement agent
            try:
                logger.info("[POST /chat] Tool(agent_service_query) args={message=%s}", req.question)
            except Exception:
                pass
            res = await _handle_tool_call("agent_service_query", {"message": req.question or ""})
            resp_text = ""
            if isinstance(res, dict):
                resp_text = (res.get("response") or "").strip()
            if not resp_text:
                msg = "I couldn't retrieve supplier information right now."
            else:
                summarized = _summarize_agent_response(resp_text, limit_per_sku=3)
                msg = summarized or resp_text
            try:
                if req.conversation_id:
                    _memory.append(req.conversation_id, "user", req.question)
                    _memory.append(req.conversation_id, "assistant", msg)
            except Exception:
                pass
            yield msg
            return

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
