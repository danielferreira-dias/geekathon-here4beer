export type ForecastItem = {
  sku: string;
  forecasted_demand: number;
  confidence_or_reason: string;
};

export type ProductionPlanItem = {
  sku: string;
  forecasted_demand: number;
  current_inventory: number;
  suggested_production: number;
};

export type RawMaterialOrderItem = {
  material_id: string;
  needed_qty_kg: number;
  current_stock_kg: number;
  suggested_order_kg: number;
};

export type RiskAlertItem = {
  alert_type: "expiry" | "stockout" | "overstock" | "shortage" | "other";
  description: string;
  sku_or_material: string;
};

export type AnalysisResult = {
  forecast_table: ForecastItem[];
  production_plan: ProductionPlanItem[];
  raw_material_orders: RawMaterialOrderItem[];
  risk_alerts: RiskAlertItem[];
  summary_text: string;
};

// Legacy types for backward compatibility (can be removed later)
export type PlanItem = ProductionPlanItem;
export type OrderItem = RawMaterialOrderItem;
export type RiskItem = RiskAlertItem;
