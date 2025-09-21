import os
import json
import logging
from typing import Dict, Any, List

import requests
from sqlalchemy import select, desc

from db import SessionLocal
import models as db_models


def get_risks() -> Dict[str, Any]:
    """
    Analyze expiry and stockout risks from the latest run.
    - Stockout risk: forecasted_demand > current_inventory for any SKU in ProductionPlan
    - Expiry risk: if RiskAlert table has entries of type 'expiry' for the run (fallback: none)
    Returns a JSON-serializable dict with lists and a short summary.
    """
    with SessionLocal() as session:
        # latest run
        row = session.execute(select(db_models.Run.id).order_by(desc(db_models.Run.created_at)).limit(1)).first()
        if not row:
            return {"run_id": None, "risks": [], "summary": "No runs found"}
        run_id = row[0]

        risks: List[Dict[str, Any]] = []
        # Stockout risks from production plans
        plans = session.execute(select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == run_id)).scalars().all()
        for p in plans:
            if int(p.forecasted_demand) > int(p.current_inventory):
                risks.append({
                    "type": "stockout",
                    "sku": p.sku,
                    "detail": f"forecast {p.forecasted_demand} > inventory {p.current_inventory}",
                })

        # Expiry risks from stored alerts if present
        exp = session.execute(
            select(db_models.RiskAlert).where(
                (db_models.RiskAlert.run_id == run_id) & (db_models.RiskAlert.alert_type == 'expiry')
            )
        ).scalars().all()
        for e in exp:
            risks.append({
                "type": "expiry",
                "sku_or_material": e.sku_or_material,
                "detail": e.description,
            })

        # Compose summary string
        parts = []
        stockout_items = [r for r in risks if r.get("type") == "stockout"]
        expiry_items = [r for r in risks if r.get("type") == "expiry"]
        if expiry_items:
            for e in expiry_items[:5]:
                label = e.get("sku_or_material") or "item"
                parts.append(f"- {label}: {e.get('detail')}")
        if stockout_items:
            for s in stockout_items[:5]:
                parts.append(f"- {s.get('sku')}: stockout risk ({s.get('detail')})")
        if not parts:
            parts.append("- No major risks detected in the latest run.")

        summary = "\n".join(["\ud83d\udcca Daily Risk Briefing", *parts])

        return {"run_id": run_id, "risks": risks, "summary": summary}


def post_briefing(summary: str) -> Dict[str, Any]:
    """
    If SLACK_WEBHOOK_URL is set, POST the summary to Slack; else log to stdout.
    """
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if webhook:
        try:
            resp = requests.post(webhook, json={"text": summary}, timeout=5)
            ok = resp.status_code // 100 == 2
            return {"posted": ok, "status": resp.status_code}
        except Exception as e:
            return {"posted": False, "error": str(e)}
    else:
        print(summary)
        return {"posted": False, "stdout": True}
