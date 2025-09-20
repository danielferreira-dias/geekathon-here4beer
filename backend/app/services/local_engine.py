import io
from typing import Dict, Any, List, Optional

import pandas as pd
from datetime import datetime, timedelta


def _read_csv_text(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_text))


def _safe_int(x) -> int:
    try:
        return int(round(float(x)))
    except Exception:
        return 0


def compute_local_plan(
    sales_csv: str,
    inventory_csv: str,
    raw_materials_csv: str,
    bom_csv: str,
    events_csv: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic local planner as a fallback when Bedrock is unavailable.
    Uses simple averages and rules to produce a result that varies with inputs.
    """
    # Parse inputs
    sales_df = _read_csv_text(sales_csv)
    inv_df = _read_csv_text(inventory_csv)
    rm_df = _read_csv_text(raw_materials_csv)
    bom_df = _read_csv_text(bom_csv)

    # Normalize column names
    sales_df.columns = [c.strip() for c in sales_df.columns]
    inv_df.columns = [c.strip() for c in inv_df.columns]
    rm_df.columns = [c.strip() for c in rm_df.columns]
    bom_df.columns = [c.strip() for c in bom_df.columns]

    # Ensure expected columns exist, attempt best-effort mapping
    # raw_materials can come as material_id or sku in provided samples
    if "material_id" not in rm_df.columns and "sku" in rm_df.columns:
        rm_df = rm_df.rename(columns={"sku": "material_id"})

    # Coerce numerics
    for df, cols in [
        (sales_df, ["units_sold"]),
        (inv_df, ["units_in_stock"]),
        (rm_df, ["units_in_stock"]),
        (bom_df, ["quantity_needed_per_unit"]),
    ]:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Dates
    for df, col in [
        (sales_df, "date"),
        (inv_df, "expiry_date"),
        (rm_df, "expiry_date"),
    ]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Forecast: average daily sales per SKU * 7
    # Also create a simple trend descriptor comparing last 2 days avg vs overall avg
    forecast_items: List[Dict[str, Any]] = []
    if not sales_df.empty and {"sku", "units_sold"}.issubset(sales_df.columns):
        # group by sku
        for sku, g in sales_df.groupby("sku"):
            avg_daily = g["units_sold"].mean()
            # trend: last 2 rows average vs overall
            recent_avg = g.sort_values("date")["units_sold"].tail(2).mean() if "date" in g.columns else avg_daily
            if avg_daily > 0:
                change = (recent_avg - avg_daily) / avg_daily
            else:
                change = 0.0
            if change > 0.08:
                reason = f"trend up {int(round(change*100))}%"
            elif change < -0.08:
                reason = f"trend down {int(round(abs(change)*100))}%"
            else:
                reason = "stable demand"
            forecast = _safe_int(avg_daily * 7)
            forecast_items.append({
                "sku": str(sku),
                "forecasted_demand": forecast,
                "confidence_or_reason": reason,
            })

    # Inventory lookup
    inv_map = {}
    if not inv_df.empty and {"sku", "units_in_stock"}.issubset(inv_df.columns):
        inv_map = (
            inv_df.set_index("sku")["units_in_stock"].to_dict()
        )

    # Production plan
    production_plan: List[Dict[str, Any]] = []
    for fi in forecast_items:
        sku = fi["sku"]
        forecast = _safe_int(fi["forecasted_demand"])
        current = _safe_int(inv_map.get(sku, 0))
        suggested = max(0, forecast - current)
        production_plan.append({
            "sku": sku,
            "forecasted_demand": forecast,
            "current_inventory": current,
            "suggested_production": suggested,
        })

    # Raw material needs from BOM
    # Merge production_plan with BOM on sku to compute material quantities
    raw_orders: List[Dict[str, Any]] = []
    if production_plan and not bom_df.empty and {"sku", "material_id", "quantity_needed_per_unit"}.issubset(bom_df.columns):
        pp_df = pd.DataFrame(production_plan)
        need_df = pp_df.merge(bom_df, on="sku", how="left")
        need_df["needed_qty"] = need_df["suggested_production"] * need_df["quantity_needed_per_unit"]
        mat_need = need_df.groupby("material_id")["needed_qty"].sum().reset_index()
        # current stock map for materials
        rm_stock = {}
        if not rm_df.empty and {"material_id", "units_in_stock"}.issubset(rm_df.columns):
            rm_stock = rm_df.set_index("material_id")["units_in_stock"].to_dict()
        for _, row in mat_need.iterrows():
            mid = str(row["material_id"]) if pd.notna(row["material_id"]) else ""
            needed = _safe_int(row["needed_qty"])
            current_stock = _safe_int(rm_stock.get(mid, 0))
            order = max(0, needed - current_stock)
            raw_orders.append({
                "material_id": mid,
                "needed_qty_kg": needed,
                "current_stock_kg": current_stock,
                "suggested_order_kg": order,
            })

    # Risks: expiry within next 3-7 days
    risk_alerts: List[Dict[str, Any]] = []
    today = datetime.utcnow().date()
    soon = today + timedelta(days=7)
    # Finished goods expiry
    if {"sku", "expiry_date", "units_in_stock"}.issubset(inv_df.columns):
        for _, row in inv_df.iterrows():
            exp = row.get("expiry_date")
            if pd.notna(exp):
                d = pd.to_datetime(exp, errors="coerce").date() if not isinstance(exp, (datetime, pd.Timestamp)) else exp.date()
                days = (d - today).days
                if 0 <= days <= 7 and _safe_int(row.get("units_in_stock", 0)) > 0:
                    qty = _safe_int(row.get("units_in_stock", 0))
                    sku = str(row.get("sku", ""))
                    risk_alerts.append({
                        "alert_type": "expiry",
                        "description": f"{qty} {sku} expire in {days} days",
                        "sku_or_material": sku,
                    })
    # Raw materials expiry
    if {"material_id", "expiry_date", "units_in_stock"}.issubset(rm_df.columns):
        for _, row in rm_df.iterrows():
            exp = row.get("expiry_date")
            if pd.notna(exp):
                d = pd.to_datetime(exp, errors="coerce").date() if not isinstance(exp, (datetime, pd.Timestamp)) else exp.date()
                days = (d - today).days
                if 0 <= days <= 7 and _safe_int(row.get("units_in_stock", 0)) > 0:
                    qty = _safe_int(row.get("units_in_stock", 0))
                    mid = str(row.get("material_id", ""))
                    risk_alerts.append({
                        "alert_type": "expiry",
                        "description": f"{qty} units of {mid} expire in {days} days",
                        "sku_or_material": mid,
                    })

    # Stockout risks based on forecast vs inventory
    for pp in production_plan:
        if pp["suggested_production"] > 0:
            sku = pp["sku"]
            risk_alerts.append({
                "alert_type": "stockout",
                "description": f"Inventory below forecast for {sku}",
                "sku_or_material": sku,
            })

    # Summary text
    top = max(production_plan, key=lambda x: x["suggested_production"], default=None)
    if top:
        summary = (
            f"Key focus: {top['sku']} — produce {top['suggested_production']} to meet forecast of {top['forecasted_demand']}. "
            f"Check raw material orders and expiry risks."
        )
    else:
        summary = "Demand appears covered by inventory. Monitor expiries and events."

    return {
        "forecast_table": forecast_items,
        "production_plan": production_plan,
        "raw_material_orders": raw_orders,
        "risk_alerts": risk_alerts,
        "summary_text": summary,
    }
