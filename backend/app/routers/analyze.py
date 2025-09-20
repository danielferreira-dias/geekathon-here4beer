from typing import Optional
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas import AnalyzeResponse
from app.services.bedrock import BedrockClient
from app.services.prompt import SYSTEM_PROMPT, build_user_prompt
from app.utils.csv_utils import upload_to_csv_text
from app.services.local_engine import compute_local_plan
from db_utils import save_analysis

# New imports for GET endpoint
from sqlalchemy import select, desc
from db import SessionLocal
import models as db_models

router = APIRouter(prefix="/analyze", tags=["analyze"])


def get_bedrock_client() -> BedrockClient:
    return BedrockClient()


@router.post("")
async def analyze(
    notes: Optional[str] = Form(None, description="Optional notes for this run"),
    sales_history: UploadFile = File(..., description="CSV/XLSX of sales history"),
    inventory: UploadFile = File(..., description="CSV/XLSX of inventory"),
    raw_materials: UploadFile = File(..., description="CSV/XLSX of raw materials"),
    bill_of_materials: UploadFile = File(..., description="CSV/XLSX of bill of materials"),
    events: Optional[UploadFile] = File(None, description="CSV/XLSX of events (optional)"),
    bedrock: BedrockClient = Depends(get_bedrock_client),
):
    try:
        sales_csv = upload_to_csv_text(sales_history)
        inventory_csv = upload_to_csv_text(inventory)
        raw_materials_csv = upload_to_csv_text(raw_materials)
        bom_csv = upload_to_csv_text(bill_of_materials)
        events_csv = upload_to_csv_text(events) if events is not None else None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_prompt = build_user_prompt(
        sales_csv=sales_csv,
        inventory_csv=inventory_csv,
        raw_materials_csv=raw_materials_csv,
        bom_csv=bom_csv,
        events_csv=events_csv,
    )

    raw = bedrock.generate_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

    try:
        validated = AnalyzeResponse.model_validate(raw)
    except ValidationError as ve:
        raise HTTPException(status_code=502, detail=f"Model produced invalid schema: {ve}")

    # Generate a run_id
    run_id = str(uuid.uuid4())

    # Override summary_text to a concise, consistent format matching GET /analyze
    try:
        stockout_count = sum(
            1 for p in validated.production_plan if int(p.forecasted_demand) > int(p.current_inventory)
        )
        expiry_count = sum(
            1 for r in validated.risk_alerts if str(getattr(r, "alert_type", "")).lower() == "expiry"
        )
        validated.summary_text = (
            f"Analysis for run {run_id}. Stockout risks: {stockout_count}. Expiry alerts: {expiry_count}."
        )
    except Exception:
        # If anything goes wrong computing the concise summary, fall back to existing summary_text
        pass

    # Persist results for use in /chat and future queries
    try:
        save_analysis(run_id=run_id, analysis_json=validated.model_dump(), notes=notes)
    except Exception as e:
        # If saving fails, surface a server error explaining the issue
        raise HTTPException(status_code=500, detail=f"Failed to save analysis for run_id {run_id}: {e}")

    response_payload = {"run_id": run_id, **validated.model_dump()}
    return JSONResponse(content=response_payload)


@router.get("")
async def get_latest_analysis():
    """Return the most recent analysis in the same shape as POST /analyze.
    It loads the latest run_id from the DB and reconstructs the AnalyzeResponse payload.
    """
    with SessionLocal() as session:
        # Find latest run_id
        row = session.execute(select(db_models.Run.id).order_by(desc(db_models.Run.created_at)).limit(1)).first()
        if not row:
            raise HTTPException(status_code=404, detail="No runs found")
        run_id = row[0]

        # Load tables
        forecasts = session.execute(select(db_models.Forecast).where(db_models.Forecast.run_id == run_id)).scalars().all()
        plans = session.execute(select(db_models.ProductionPlan).where(db_models.ProductionPlan.run_id == run_id)).scalars().all()
        orders = session.execute(select(db_models.RawMaterialOrder).where(db_models.RawMaterialOrder.run_id == run_id)).scalars().all()
        alerts = session.execute(select(db_models.RiskAlert).where(db_models.RiskAlert.run_id == run_id)).scalars().all()

        payload = {
            "forecast_table": [
                {
                    "sku": f.sku,
                    "forecasted_demand": int(f.forecasted_demand),
                    "confidence_or_reason": f.confidence_or_reason,
                }
                for f in forecasts
            ],
            "production_plan": [
                {
                    "sku": p.sku,
                    "forecasted_demand": int(p.forecasted_demand),
                    "current_inventory": int(p.current_inventory),
                    "suggested_production": int(p.suggested_production),
                }
                for p in plans
            ],
            "raw_material_orders": [
                {
                    "material_id": o.material_id,
                    "needed_qty_kg": int(o.needed_qty_kg),
                    "current_stock_kg": int(o.current_stock_kg),
                    "suggested_order_kg": int(o.suggested_order_kg),
                }
                for o in orders
            ],
            "risk_alerts": [
                {
                    "alert_type": r.alert_type,
                    "description": r.description,
                    "sku_or_material": r.sku_or_material,
                }
                for r in alerts
            ],
        }

        # Derive a brief summary_text to fulfill the schema contract
        stockout_count = sum(1 for p in plans if int(p.forecasted_demand) > int(p.current_inventory))
        expiry_count = sum(1 for r in alerts if (r.alert_type or "").lower() == "expiry")
        payload["summary_text"] = (
            f"Analysis for run {run_id}. Stockout risks: {stockout_count}. Expiry alerts: {expiry_count}."
        )

        # Validate against schema (ensures RiskAlert.severity is added)
        try:
            validated = AnalyzeResponse.model_validate(payload)
        except ValidationError as ve:
            raise HTTPException(status_code=500, detail=f"Failed to build response for {run_id}: {ve}")

        return JSONResponse(content={"run_id": run_id, **validated.model_dump()})
