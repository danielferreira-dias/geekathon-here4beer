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

    # Generate a run_id and persist results for use in /chat and future queries
    run_id = str(uuid.uuid4())
    try:
        save_analysis(run_id=run_id, analysis_json=validated.model_dump(), notes=notes)
    except Exception as e:
        # If saving fails, surface a server error explaining the issue
        raise HTTPException(status_code=500, detail=f"Failed to save analysis for run_id {run_id}: {e}")

    response_payload = {"run_id": run_id, **validated.model_dump()}
    return JSONResponse(content=response_payload)
