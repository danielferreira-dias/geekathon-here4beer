import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Set, Optional, Tuple
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


# ---- Structured per-conversation context for focus SKUs, suppliers, etc. ----
class ConversationContext:
    def __init__(self, max_conversations: int = 200):
        self.max_conversations = max_conversations
        self._ctx: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def get(self, conv_id: Optional[str]) -> Dict[str, Any]:
        if not conv_id:
            return {}
        if conv_id in self._ctx:
            self._ctx.move_to_end(conv_id)
            return self._ctx[conv_id]
        return {}

    def update(self, conv_id: Optional[str], **kv):
        if not conv_id:
            return
        ctx = self._ctx.get(conv_id) or {}
        ctx.update({k: v for k, v in kv.items() if v is not None})
        self._ctx[conv_id] = ctx
        while len(self._ctx) > self.max_conversations:
            self._ctx.popitem(last=False)

    def clear(self, conv_id: Optional[str]):
        if conv_id in self._ctx:
            del self._ctx[conv_id]


_memory = ConversationMemory()
_ctx = ConversationContext()


class ChatRequest(BaseModel):
    question: str
    run_id: Optional[str] = None
    conversation_id: Optional[str] = None


def _schema_from_metadata() -> Tuple[str, List[str], Dict[str, Set[str]]]:
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


# Tool specs exposed to Bedrock (kept for reference)
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
        # ---- retry on throttling/5xx with exponential backoff
        attempts = 3
        backoffs = [1.0, 2.0]  # seconds
        for i in range(attempts):
            try:
                logger.info("[AgentServiceTool] Calling %s with payload=%s", AGENT_SERVICE_QUERY_URL, payload)
                r = requests.post(AGENT_SERVICE_QUERY_URL, json=payload, timeout=12)
                text = r.text
                try:
                    data = r.json()
                except Exception:
                    data = {"response": text}
                logger.info("[AgentServiceTool] Status=%s Response=%s", r.status_code, data)
                # Retry on 5xx/throttling
                if r.status_code >= 500 or ("ThrottlingException" in text):
                    if i < attempts - 1:
                        await asyncio.sleep(backoffs[i])
                        continue
                return {"response": data.get("response")}
            except Exception as e:
                logger.exception("[AgentServiceTool] ERROR calling service (attempt %s): %s", i + 1, e)
                if i < attempts - 1:
                    await asyncio.sleep(backoffs[i])
                    continue
                return {"error": f"agent_service_query failed: {e}"}

        return {"error": "agent_service_query failed after retries."}

    return {"error": f"Unknown tool: {name}"}


# ---------- Supplier response summarization / formatting ----------
def _summarize_agent_response(resp_text: str, limit_per_sku: int = 3) -> str:
    """Summarize the external procurement agent response into concise, context-aware bullets.
    Accepts markdown headings like '## Providers selling ...'.
    """
    if not resp_text:
        return ""
    lines = resp_text.splitlines()
    sections: Dict[str, List[Dict[str, Any]]] = {}
    current_sku: Optional[str] = None

    header_re = re.compile(
        r"^\s*(?:[#*\-\d\.]+\s*)?providers selling ['\"]?([^'\"]+)['\"]?:\s*$",
        re.IGNORECASE,
    )
    price_re = re.compile(r"\$(\d+(?:\.\d+)?)")
    stock_re = re.compile(r"stock:\s*(\d+)", re.IGNORECASE)
    dist_re = re.compile(r"distance:\s*(\d+)\s*km", re.IGNORECASE)

    for raw in lines:
        s = raw.strip()
        m = header_re.match(s)
        if m:
            current_sku = m.group(1).strip().replace(" ", "_")
            sections.setdefault(current_sku, [])
            continue
        if s.startswith("- "):
            name = None
            price: Optional[float] = None
            stock: Optional[int] = None
            distance_km: Optional[int] = None
            content = s[2:]
            if ':' in content:
                name = content.split(':', 1)[0].strip()
            else:
                name = content.split(' - ', 1)[0].strip()
            pm = price_re.search(s)
            if pm:
                try:
                    price = float(pm.group(1))
                except Exception:
                    price = None
            sm = stock_re.search(s)
            if sm:
                try:
                    stock = int(sm.group(1))
                except Exception:
                    stock = None
            dm = dist_re.search(s)
            if dm:
                try:
                    distance_km = int(dm.group(1))
                except Exception:
                    distance_km = None
            entry = {"name": name, "price": price, "stock": stock, "distance_km": distance_km, "raw": s}
            if current_sku:
                sections.setdefault(current_sku, [])
                sections[current_sku].append(entry)
            else:
                sections.setdefault("__unscoped__", [])
                sections["__unscoped__"].append(entry)

    out: List[str] = []
    section_keys = [k for k in sections.keys() if k != "__unscoped__"]
    if section_keys:
        out.append("Supplier suggestions (top options):")
        for sku in section_keys:
            providers = (sections.get(sku) or [])[:limit_per_sku]
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
                if p.get("price") is not None and (best_price is None or p['price'] < best_price):
                    best_price = p['price']; best_name = p.get("name")
            line = f"- {sku}: " + ", ".join(parts)
            if best_price is not None and best_name:
                line += f". Best price: {best_name} (${best_price:.2f})"
            out.append(line)
        return "\n".join(out)

    bullets = sections.get("__unscoped__", [])
    if bullets:
        out.append("Top supplier options:")
        for p in bullets[:limit_per_sku]:
            out.append(p.get("raw") or "")
        return "\n".join(out).strip()

    return "\n".join(lines[:8]).strip()


def _prettify_supplier_summary(summary_text: str, focus_skus: Optional[List[str]] = None) -> str:
    """
    Convert summarized supplier lines into your house style:

    **Supplier options (bread loaf)**
    1) A — $2.99 — stock 400 — 12 km  *(best price)*
    2) B — $5.99 — stock 150 — 12 km
    3) C — $6.25 — stock 110 — 14 km
    """
    if not summary_text:
        return ""

    lines = [ln.strip() for ln in summary_text.splitlines() if ln.strip()]
    sku_lines = [ln for ln in lines if ln.startswith("- ") and ":" in ln]
    if not sku_lines:
        return summary_text

    blocks: List[str] = []
    allowed = set(focus_skus or [])

    for ln in sku_lines:
        head, tail = ln[2:].split(":", 1)
        sku = head.strip()
        if allowed and sku not in allowed:
            continue

        best_match = re.search(r"Best price:\s*([^\(]+)\s*\(\$(\d+(?:\.\d+)?)\)", tail, re.IGNORECASE)
        best_name = (best_match.group(1).strip() if best_match else None)

        # Remove the "Best price: ..." sentence from tail before parsing providers
        tail = re.sub(r"\.\s*Best price:.*$", "", tail).strip().strip(".")

        providers = [p.strip() for p in tail.split(",") if p.strip()]
        pretty_rows: List[str] = []
        for idx, pv in enumerate(providers, start=1):
            # Name is text before price/stock/dist separators
            name = re.split(r"\s\$\d|\sstock\s|\s\d+\s*km|\s—\s|\s-\s", pv, maxsplit=1)[0].strip()
            price = re.search(r"\$(\d+(?:\.\d+)?)", pv)
            stock = re.search(r"stock\s+(\d+)", pv, re.IGNORECASE)
            dist  = re.search(r"(\d+)\s*km", pv, re.IGNORECASE)

            parts = [name]
            if price: parts.append(f"${float(price.group(1)):.2f}")
            if stock: parts.append(f"stock {stock.group(1)}")
            if dist:  parts.append(f"{dist.group(1)} km")

            row = f"{idx}) " + " — ".join(parts)
            if best_name and name.lower() == best_name.lower():
                row += "  *(best price)*"
            pretty_rows.append(row)

        pretty_sku = sku.replace("_", " ")
        blocks.append("\n".join([f"**Supplier options ({pretty_sku})**"] + pretty_rows))

    return "\n\n".join(blocks).strip() or summary_text


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
    if len(top_names) == 1:
        s1 = f"Recommendation: prioritize {top_names[0]} due to the highest deficit."
    else:
        s1 = f"Recommendation: prioritize {top_names[0]} and {top_names[1]} due to the highest deficits."
    picks = []
    for it in prioritized[:4]:
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


def _coalesce_final_reply(primary_text: str, supplier_block: str, email_hint: str = "") -> str:
    """
    Build one cohesive message with consistent headings and spacing.
    """
    parts = []
    if primary_text.strip():
        parts.append(primary_text.strip())
    if supplier_block.strip():
        parts.append(supplier_block.strip())
    if email_hint.strip():
        parts.append(email_hint.strip())
    return "\n\n".join(parts)


# --------- Name → SKU inference helpers ----------
def _infer_skus_from_question(q: str, limit: int = 5) -> List[str]:
    if not q:
        return []
    ql = q.lower()
    candidates: List[str] = []
    tokens = re.findall(r"[a-z0-9_]+(?:\s+[a-z0-9_]+){0,2}", ql)
    for t in tokens:
        t = t.strip()
        if len(t) < 3:
            continue
        if t in {"what", "which", "those", "these", "stock", "stocks", "supplier", "suppliers", "buy", "purchase", "email", "order", "units", "loaves"}:
            continue
        candidates.append(t)

    skus: List[str] = []
    try:
        with engine.connect() as conn:
            for cand in candidates[:8]:
                res = conn.execute(sql_text("""
                    SELECT sku FROM products 
                    WHERE LOWER(name) LIKE :q OR LOWER(category) LIKE :q OR LOWER(sku) LIKE :q
                    LIMIT 3
                """), {"q": f"%{cand}%"})
                for row in res:
                    s = row._mapping.get("sku")
                    if s and s not in skus:
                        skus.append(s)
                if len(skus) >= limit:
                    break
    except Exception:
        pass
    return skus[:limit]


def _collect_skus_from_rows(rows: List[Dict[str, Any]]) -> List[str]:
    skus = []
    for r in rows or []:
        s = r.get("sku") or r.get("SKU") or r.get("item_sku")
        if isinstance(s, str) and s not in skus:
            skus.append(s)
    return skus


def _top_deficit_skus(rows: List[Dict[str, Any]], k: int = 4) -> List[str]:
    items: List[Tuple[str, int]] = []
    for r in rows or []:
        try:
            fd = int(r.get("forecasted_demand", 0))
            ci = int(r.get("current_inventory", 0))
            sku = r.get("sku")
            if fd > ci and isinstance(sku, str):
                items.append((sku, fd - ci))
        except Exception:
            continue
    items.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in items[:k]]


async def _fetch_supplier_summary_for_skus(sku_list: List[str], limit_per_sku: int = 3) -> Optional[str]:
    """Single batched call to the procurement agent. No per-SKU fallback."""
    if not sku_list:
        return None

    joined = ", ".join(sku_list)
    combined_msg = (
        f"Return supplier options ONLY for the following SKUs exactly: {joined}.\n"
        f"For EACH SKU, include a section titled exactly: Providers selling '{{SKU}}':\n"
        f"List up to {limit_per_sku} suppliers as bullets in the format:\n"
        f"- <Name>: $<price> - <Region> (Stock: <int>, Distance: <int>km)\n"
        f"You may use markdown headings (e.g., '## Providers selling ...'). "
        f"Do not include any other products or SKUs."
    )
    res = await _handle_tool_call("agent_service_query", {"message": combined_msg})
    resp_text = (res or {}).get("response") if isinstance(res, dict) else None
    summarized = _summarize_agent_response((resp_text or "").strip(), limit_per_sku=limit_per_sku) if resp_text else ""

    # Always post-filter to the requested SKUs only
    if summarized:
        allowed = set(sku_list)
        filtered_lines = []
        for ln in summarized.splitlines():
            m = re.match(r"^\-\s*([^:]+)\s*:", ln.strip())
            if m:
                sku = m.group(1).strip()
                if sku not in allowed:
                    continue
            filtered_lines.append(ln)
        summarized = "\n".join(filtered_lines).strip()

    return summarized or None


# ---------- Email drafting helpers ----------
def _parse_email_intent(q: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Returns: (is_email_intent, qty, sku, supplier_name)
    Understands phrases like:
      - "draft email for 500 units of bread loaf"
      - "email the best supplier for chicken_breast"
      - "order 300 chicken breasts"
      - "write an email to Root Vegetable Co for 200 bread_loaf"
      - Affirmatives only: "yes", "ok", "go ahead" (uses context to fill missing fields)
    """
    if not q:
        return False, None, None, None
    ql = q.lower().strip()

    # Affirmative-only reply (in response to our Next step)
    if re.fullmatch(r"(yes|yeah|yep|ok|okay|sure|do it|go ahead|please do|please|sounds good|let'?s do it|proceed)[\.\!\s]*", ql):
        return True, None, None, None

    # Email intent keywords
    email_triggers = ["draft email", "write an email", "email the", "email", "send an email", "send email", "order"]
    if not any(k in ql for k in email_triggers):
        return False, None, None, None

    qty = None
    sku = None
    supplier = None

    # qty
    m_qty = re.search(r"\b(\d{1,6})\s*(units|unit|pcs|pieces|loaves)?\b", ql)
    if m_qty:
        try:
            qty = int(m_qty.group(1))
        except Exception:
            qty = None

    # supplier name (after 'to'/'with'/'from')
    m_sup = re.search(r"\b(?:to|with|from)\s+([a-z0-9][a-z0-9\s&\.\-]+)$", ql.strip())
    if m_sup:
        supplier = m_sup.group(1).strip()

    # sku (after 'of ' or 'for ')
    m_sku = re.search(r"\b(?:of|for)\s+([a-z0-9_][a-z0-9_\s\-]+)", ql)
    if m_sku:
        sku = m_sku.group(1).strip().replace(" ", "_")

    return True, qty, sku, supplier


def _email_next_step_hint(skus: List[str]) -> str:
    if not skus:
        return ""
    sku_pretty = skus[0].replace("_", " ")
    # Natural-language nudge only — no code examples.
    return f"Next step: want me to draft an email order to the **best supplier** for **{sku_pretty}**?"


def _store_supplier_context(conv_id: Optional[str], providers_text: Optional[str], selected_skus: List[str]):
    if not conv_id or not providers_text:
        return
    try:
        best_map = _extract_best_suppliers_from_summary(providers_text)
        ctx = _ctx.get(conv_id)
        last_map = ctx.get("best_map") or {}
        last_map.update(best_map)
        _ctx.update(
            conv_id,
            last_supplier_summary=providers_text,
            best_map=last_map,
            last_result_skus=selected_skus or ctx.get("last_result_skus"),
        )
    except Exception:
        pass


def _get_best_supplier_for_sku(conv_id: Optional[str], sku: str) -> Optional[str]:
    if not conv_id or not sku:
        return None
    ctx = _ctx.get(conv_id)
    best_map = ctx.get("best_map") or {}
    info = best_map.get(sku)
    if info and isinstance(info.get("name"), str):
        return info["name"]
    return None


async def _draft_email_with_agent(qty: int, sku: str, supplier_name: Optional[str]) -> Optional[str]:
    if qty is None or not sku:
        return None
    sku_display = sku.replace("_", " ").strip()
    if supplier_name and supplier_name.strip().lower() not in {"best", "best supplier"}:
        msg = f"write an email to order {qty} units of {sku_display} to {supplier_name}"
    else:
        msg = f"write an email to order {qty} units of {sku_display} to the best supplier"
    res = await _handle_tool_call("agent_service_query", {"message": msg})
    return (res or {}).get("response") if isinstance(res, dict) else None


@router.post("")
async def chat(req: ChatRequest):
    schema_text, allowed_tables, schema_map = _schema_from_metadata()

    async def gen():
        # Send an early tiny chunk so proxies begin the response (we'll still buffer content)
        yield " "
        await asyncio.sleep(0.05)

        try:
            logger.info("[POST /chat] Received question. conversation_id=%s run_id=%s question=%s",
                        req.conversation_id, req.run_id, (req.question or "")[:200])
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

        # Prime focus SKUs from question text
        try:
            if req.conversation_id:
                inferred = _infer_skus_from_question(req.question)
                if inferred:
                    _ctx.update(req.conversation_id, focus_skus=inferred)
        except Exception:
            pass

        # ---------- Email intent (can be a bare "yes") ----------
        try:
            is_email, qty_req, sku_req, supplier_req = _parse_email_intent(req.question or "")
        except Exception:
            is_email, qty_req, sku_req, supplier_req = (False, None, None, None)

        if is_email:
            # Resolve SKU from context if not provided
            if not sku_req:
                ctx_focus = _ctx.get(req.conversation_id)
                focus_skus = ctx_focus.get("focus_skus") or ctx_focus.get("last_result_skus") or []
                if focus_skus:
                    sku_req = focus_skus[0]

            # Resolve qty from context (use last known deficit as a sensible default)
            if qty_req is None:
                ctx_focus = _ctx.get(req.conversation_id)
                last_deficits: Dict[str, int] = ctx_focus.get("last_deficits") or {}
                if sku_req and last_deficits.get(sku_req):
                    qty_req = int(last_deficits[sku_req])

            # Resolve supplier (prefer explicit; else best supplier in context)
            if supplier_req is None or supplier_req.strip().lower() in {"best", "best supplier"}:
                best_name = _get_best_supplier_for_sku(req.conversation_id, sku_req or "")
                supplier_name_for_prompt = best_name if best_name else "best supplier"
            else:
                supplier_name_for_prompt = supplier_req

            if not sku_req or qty_req is None:
                # Not enough info to draft; guide user succinctly
                missing = []
                if sku_req is None:
                    missing.append("SKU")
                if qty_req is None:
                    missing.append("quantity")
                guidance = " and ".join(missing)
                msg = f"I can draft the email, but I’m missing the {guidance.lower()}. For example: “500 units of bread loaf”."
                yield msg
                if req.conversation_id:
                    _memory.append(req.conversation_id, "user", req.question)
                    _memory.append(req.conversation_id, "assistant", msg)
                return

            # Draft email via agent-service
            email_text = await _draft_email_with_agent(qty_req, sku_req, supplier_name_for_prompt)
            if not email_text:
                msg = "I couldn't generate the email right now."
                yield msg
                if req.conversation_id:
                    _memory.append(req.conversation_id, "user", req.question)
                    _memory.append(req.conversation_id, "assistant", msg)
                return

            # Clean, cohesive reply with a markdown block
            final_email = f"**Draft email ({sku_req.replace('_',' ')}, {qty_req} units)**\n\n```\n{email_text.strip()}\n```"
            yield final_email
            if req.conversation_id:
                _memory.append(req.conversation_id, "user", req.question)
                _memory.append(req.conversation_id, "assistant", final_email)
            return

        # ---------- Fallback: handle "low SKUs" style questions directly via DB without Bedrock ----------
        q_lower = (req.question or "").lower()
        low_keywords = ["low", "low stock", "running low", "replenish", "reorder", "risky", "risk"]
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

                if not rows:
                    msg = "No SKUs are currently below forecasted demand in the latest run."
                    yield msg
                    try:
                        if req.conversation_id:
                            _memory.append(req.conversation_id, "user", req.question)
                            _memory.append(req.conversation_id, "assistant", msg)
                    except Exception:
                        pass
                    return

                items = []
                lines = ["**Low Stock Summary:**"]
                last_deficits: Dict[str, int] = {}
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
                    deficit = None
                    try:
                        deficit = int(fd) - int(ci)
                    except Exception:
                        pass
                    items.append({"sku": sku, "fd": fd, "ci": ci, "sp": sp, "deficit": deficit})
                    if deficit is not None:
                        lines.append(f"- {sku}: inv {ci}, forecast {fd}, deficit {deficit}, suggested_production {sp}")
                        if isinstance(deficit, int):
                            last_deficits[sku] = int(deficit)
                    else:
                        lines.append(f"- {sku}: inv {ci}, forecast {fd}, suggested_production {sp}")

                # Single batched procurement lookup for top deficits
                providers_text: Optional[str] = None
                selected_skus: List[str] = []
                try:
                    top_items = [it for it in items if isinstance(it.get('sku'), str) and it.get('deficit') is not None]
                    top_items.sort(key=lambda x: int(x.get('deficit', 0)), reverse=True)
                    top_items = top_items[:4]
                    if top_items:
                        selected_skus = [it['sku'] for it in top_items]
                        logger.info("[POST /chat] Auto-procurement (batched) for SKUs=%s", selected_skus)
                        providers_text = await _fetch_supplier_summary_for_skus(selected_skus, limit_per_sku=3)
                except Exception as e:
                    logger.exception("[POST /chat] Auto-procurement section failed: %s", e)

                primary_text = "\n".join(lines)
                pretty_suppliers = _prettify_supplier_summary(providers_text or "", selected_skus) if providers_text else ""

                # Store supplier context + deficits for email follow-up
                _store_supplier_context(req.conversation_id, providers_text, selected_skus)
                if req.conversation_id:
                    _ctx.update(req.conversation_id, last_deficits=last_deficits)

                email_hint = _email_next_step_hint(selected_skus)

                final_reply = _coalesce_final_reply(primary_text, pretty_suppliers, email_hint)

                yield final_reply
                try:
                    if req.conversation_id:
                        _memory.append(req.conversation_id, "user", req.question)
                        _memory.append(req.conversation_id, "assistant", final_reply)
                        low_skus = [it["sku"] for it in items if isinstance(it.get("sku"), str)]
                        if low_skus:
                            _ctx.update(req.conversation_id, focus_skus=low_skus, last_result_skus=low_skus)
                except Exception:
                    pass
                return
            except Exception as e:
                logger.exception("[POST /chat] Low-SKUs fallback failed: %s", e)

        # ---------- Supplier/provider intent: directly ask external procurement agent ----------
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
            try:
                conv_focus = _ctx.get(req.conversation_id)
                focus_skus: List[str] = conv_focus.get("focus_skus") or conv_focus.get("last_result_skus") or []
                inferred = _infer_skus_from_question(req.question)
                merged_skus = list(OrderedDict.fromkeys([*inferred, *focus_skus]))[:4]

                if not merged_skus:
                    res = await _handle_tool_call("agent_service_query", {"message": req.question or ""})
                    resp_text = (res or {}).get("response") if isinstance(res, dict) else ""
                    summarized = _summarize_agent_response(resp_text or "", limit_per_sku=3) if resp_text else ""
                    final_reply = _prettify_supplier_summary(summarized, None) if summarized else "I could not find matching suppliers."
                    # Store for follow-ups
                    _store_supplier_context(req.conversation_id, summarized, [])
                    if req.conversation_id:
                        _memory.append(req.conversation_id, "user", req.question)
                        _memory.append(req.conversation_id, "assistant", final_reply)
                    yield final_reply
                    return

                providers_text = await _fetch_supplier_summary_for_skus(merged_skus, limit_per_sku=3)
                final_pretty = _prettify_supplier_summary(providers_text or "", merged_skus) if providers_text else "No supplier matches for the requested items."

                # Store for follow-ups
                _store_supplier_context(req.conversation_id, providers_text, merged_skus)

                email_hint = _email_next_step_hint(merged_skus)
                final = _coalesce_final_reply(final_pretty, "", email_hint)

                if req.conversation_id:
                    _memory.append(req.conversation_id, "user", req.question)
                    _memory.append(req.conversation_id, "assistant", final)
                    _ctx.update(req.conversation_id, focus_skus=merged_skus, last_result_skus=merged_skus)

                yield final
                return
            except Exception as e:
                logger.exception("[POST /chat] Supplier intent handling failed: %s", e)
                yield "I could not retrieve supplier information right now."
                return

        # ---------- General path via Bedrock (SQL generation + explanation) ----------
        br = _bedrock_client()
        if br is None:
            logger.info("[POST /chat] Bedrock not configured; responding with guidance")
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
            logger.info("[POST /chat] Generated SQL (truncated): %s", sql_query[:200])
        except Exception as e:
            logger.exception("[POST /chat] Error generating SQL: %s", e)
            yield f"Error generating SQL: {e}"
            return

        if not is_safe_sql(sql_query, allowed_tables, schema_map):
            logger.info("[POST /chat] Generated SQL failed safety checks; refusing to execute.")
            yield "I couldn't generate a safe SQL query."
            return

        # Run SQL
        rows: List[Dict[str, Any]] = []
        try:
            logger.info("[POST /chat] Executing SQL...")
            with engine.connect() as conn:
                result = conn.execute(sql_text(sql_query))
                for r in result:
                    rows.append(dict(r._mapping))
            logger.info("[POST /chat] SQL executed. rows=%d", len(rows))
        except Exception as e:
            logger.exception("[POST /chat] SQL execution error: %s", e)
            yield f"SQL execution error: {e}"
            return

        try:
            last_deficits: Dict[str, int] = {}
            for r in rows:
                sku = r.get("sku")
                fd = r.get("forecasted_demand")
                ci = r.get("current_inventory")
                if isinstance(sku, str) and fd is not None and ci is not None:
                    try:
                        d = int(fd) - int(ci)
                        if d > 0:
                            last_deficits[sku] = d
                    except Exception:
                        pass
            if last_deficits and req.conversation_id:
                ctx_existing = _ctx.get(req.conversation_id)
                merged = dict(ctx_existing.get("last_deficits") or {})
                merged.update(last_deficits)
                _ctx.update(req.conversation_id, last_deficits=merged)
        except Exception:
            pass

        # Update focus SKUs from rows
        try:
            focus_from_rows = _collect_skus_from_rows(rows)
            if focus_from_rows and req.conversation_id:
                _ctx.update(req.conversation_id, focus_skus=focus_from_rows, last_result_skus=focus_from_rows)
        except Exception:
            pass

        # Proactive supplier suggestions for deficits (single batched call)
        pretty_suppliers = ""
        top_skus_for_auto: List[str] = []
        try:
            top_skus_for_auto = _top_deficit_skus(rows)
            if top_skus_for_auto:
                prov = await _fetch_supplier_summary_for_skus(top_skus_for_auto, limit_per_sku=3)
                if prov:
                    pretty_suppliers = _prettify_supplier_summary(prov, top_skus_for_auto)
                    _store_supplier_context(req.conversation_id, prov, top_skus_for_auto)
        except Exception:
            pass

        # Explain with "streaming" but buffer, then emit once
        explain_user = (
            "Explain these results in plain English for a supply chain planner. Be concise and clear. "
            "You may rely on the prior conversation for context if relevant.\n\n"
            f"User question (may be a follow-up): {req.question}\n\n"
            + json.dumps(rows)[:6000]
        )
        assistant_chunks: List[str] = []
        try:
            logger.info("[POST /chat] Starting buffered explanation...")
            async for chunk in _stream_bedrock_explanation(
                br,
                model_id=_model_id(),
                explain_text=explain_user,
                history_msgs=history_msgs,
            ):
                assistant_chunks.append(chunk)
            logger.info("[POST /chat] Buffered explanation completed. total_chunks=%d", len(assistant_chunks))
        except Exception as e:
            logger.exception("[POST /chat] Streaming failed: %s", e)
            yield f"Streaming failed: {e}"
            return

        primary_text = "".join(assistant_chunks).strip()

        # Email hint (natural language only) if we have supplier info
        email_hint = _email_next_step_hint(top_skus_for_auto) if pretty_suppliers else ""

        final_reply = _coalesce_final_reply(primary_text, pretty_suppliers, email_hint)

        # Emit one cohesive message
        yield final_reply

        # Persist this turn
        try:
            if conv_id:
                _memory.append(conv_id, "user", req.question)
                _memory.append(conv_id, "assistant", final_reply)
        except Exception:
            pass

    return StreamingResponse(
        gen(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# Streaming helpers (we buffer outputs; we don't stream to the client mid-reply)
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
                    await asyncio.sleep(0.02)
            stop_evt = event.get("messageStop")
            if stop_evt is not None:
                break
        return

    # Fallback: non-streaming response, chunk manually (still buffered to user)
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
    # Emit buffered chunks to our caller (we'll join them before returning to the client)
    chunk_size = 128
    for i in range(0, len(full_text), chunk_size):
        yield full_text[i:i+chunk_size]
        await asyncio.sleep(0.04)
