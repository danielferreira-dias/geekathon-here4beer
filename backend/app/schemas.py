from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


class ForecastItem(BaseModel):
    sku: str
    forecasted_demand: int = Field(ge=0)
    confidence_or_reason: Optional[str] = None


class ProductionPlanItem(BaseModel):
    sku: str
    forecasted_demand: int = Field(ge=0)
    current_inventory: int = Field(ge=0)
    suggested_production: int = Field(ge=0)


class RawMaterialOrder(BaseModel):
    material_id: str
    needed_qty_kg: int = Field(ge=0)
    current_stock_kg: int = Field(ge=0)
    suggested_order_kg: int = Field(ge=0)


class RiskAlert(BaseModel):
    alert_type: str
    severity: Literal["high", "medium", "low"]
    description: str
    sku_or_material: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _compute_severity(cls, data):
        # Ensure severity is always set and consistent with mapping rules
        if isinstance(data, dict):
            at = str(data.get("alert_type", "")).lower()
            if at in {"expiry", "stockout"}:
                sev = "high"
            elif at in {"shortage", "overstock"}:
                sev = "medium"
            elif at == "other":
                sev = "low"
            else:
                # Default to medium for any unknown alert_type values
                sev = "medium"
            data = {**data, "severity": sev}
        return data


class AnalyzeResponse(BaseModel):
    forecast_table: List[ForecastItem]
    production_plan: List[ProductionPlanItem]
    raw_material_orders: List[RawMaterialOrder]
    risk_alerts: List[RiskAlert]
    summary_text: str
