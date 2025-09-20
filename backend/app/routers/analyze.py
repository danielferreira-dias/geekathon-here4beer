from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas import AnalyzeResponse
from app.services.bedrock import BedrockClient
from app.services.prompt import SYSTEM_PROMPT, build_user_prompt
from app.utils.csv_utils import upload_to_csv_text
from app.services.local_engine import compute_local_plan

router = APIRouter(prefix="/analyze", tags=["analyze"])


def get_bedrock_client() -> BedrockClient:
    return BedrockClient()


@router.post("")
async def analyze(
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

    # If Bedrock returned the static mock (e.g., due to missing AWS/config),
    # compute a deterministic local plan based on the uploaded CSVs so output varies with inputs.
    try:
        if raw == BedrockClient._mock_response():
            raw = compute_local_plan(
                sales_csv=sales_csv,
                inventory_csv=inventory_csv,
                raw_materials_csv=raw_materials_csv,
                bom_csv=bom_csv,
                events_csv=events_csv,
            )

        validated = AnalyzeResponse.model_validate(raw)
    except ValidationError as ve:
        # If model responded with invalid JSON, fall back to local deterministic engine
        try:
            raw = compute_local_plan(
                sales_csv=sales_csv,
                inventory_csv=inventory_csv,
                raw_materials_csv=raw_materials_csv,
                bom_csv=bom_csv,
                events_csv=events_csv,
            )
            validated = AnalyzeResponse.model_validate(raw)
        except Exception:
            # If even local validation fails, propagate the original error
            raise HTTPException(status_code=502, detail=f"Model produced invalid schema: {ve}")

    return JSONResponse(content=validated.model_dump())
