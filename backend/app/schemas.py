from typing import List, Optional
from pydantic import BaseModel, Field


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
    description: str
    sku_or_material: Optional[str] = None


class AnalyzeResponse(BaseModel):
    forecast_table: List[ForecastItem]
    production_plan: List[ProductionPlanItem]
    raw_material_orders: List[RawMaterialOrder]
    risk_alerts: List[RiskAlert]
    summary_text: str
