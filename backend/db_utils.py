from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from db import SessionLocal
from models import Run, Forecast, ProductionPlan, RawMaterialOrder, RiskAlert


def save_analysis(run_id: str, analysis_json: Dict[str, Any], notes: Optional[str] = None) -> None:
    """
    Persist analysis into DB tables with the given run_id.

    analysis_json expects keys: forecast_table, production_plan, raw_material_orders, risk_alerts, summary_text
    """
    session: Session = SessionLocal()
    try:
        run = session.get(Run, run_id)
        if not run:
            run = Run(id=run_id, created_at=datetime.utcnow(), notes=notes)
            session.add(run)
            session.flush()
        elif notes is not None:
            run.notes = notes

        # Clear prior data for this run_id to keep idempotent inserts
        session.query(Forecast).filter_by(run_id=run_id).delete()
        session.query(ProductionPlan).filter_by(run_id=run_id).delete()
        session.query(RawMaterialOrder).filter_by(run_id=run_id).delete()
        session.query(RiskAlert).filter_by(run_id=run_id).delete()

        # Insert forecasts
        for item in analysis_json.get("forecast_table", []) or []:
            session.add(
                Forecast(
                    run_id=run_id,
                    sku=str(item.get("sku", "")),
                    forecasted_demand=int(item.get("forecasted_demand", 0) or 0),
                    confidence_or_reason=(item.get("confidence_or_reason") or None),
                )
            )

        # Insert production plans
        for item in analysis_json.get("production_plan", []) or []:
            session.add(
                ProductionPlan(
                    run_id=run_id,
                    sku=str(item.get("sku", "")),
                    forecasted_demand=int(item.get("forecasted_demand", 0) or 0),
                    current_inventory=int(item.get("current_inventory", 0) or 0),
                    suggested_production=int(item.get("suggested_production", 0) or 0),
                )
            )

        # Insert raw material orders
        for item in analysis_json.get("raw_material_orders", []) or []:
            session.add(
                RawMaterialOrder(
                    run_id=run_id,
                    material_id=str(item.get("material_id", "")),
                    needed_qty_kg=int(item.get("needed_qty_kg", 0) or 0),
                    current_stock_kg=int(item.get("current_stock_kg", 0) or 0),
                    suggested_order_kg=int(item.get("suggested_order_kg", 0) or 0),
                )
            )

        # Insert risk alerts
        for item in analysis_json.get("risk_alerts", []) or []:
            session.add(
                RiskAlert(
                    run_id=run_id,
                    alert_type=str(item.get("alert_type", "")),
                    sku_or_material=(item.get("sku_or_material") or None),
                    description=str(item.get("description", "")),
                )
            )

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
