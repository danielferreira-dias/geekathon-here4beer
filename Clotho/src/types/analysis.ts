export type ForecastItem = { sku: string; date: string; qty: number };
export type PlanItem = {
  sku: string;
  date: string;
  qtyToProduce: number;
  line?: string;
};
export type OrderItem = {
  material: string;
  qty: number;
  uom: string;
  neededBy: string;
  supplier?: string;
  estCost?: number;
};
export type RiskItem = {
  type: "expiry" | "shortage" | "overstock" | "other";
  skuOrMaterial: string;
  severity: "low" | "medium" | "high";
  message: string;
};
export type AnalysisResult = {
  forecast: ForecastItem[];
  productionPlan: PlanItem[];
  rawOrders: OrderItem[];
  risks: RiskItem[];
  summary: string;
};
