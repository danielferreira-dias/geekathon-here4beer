from textwrap import dedent
from typing import Optional

SYSTEM_PROMPT = (
    "You are an AI Forecasting and Planning Copilot for a meat factory.\n"
    "Behave as an expert in supply chain and data analysis.\n"
    "Analyze the provided CSV-like tables and output STRICT JSON ONLY that conforms to the requested schema.\n"
    "No commentary, no markdown, no additional keys – just one JSON object."
)


def build_user_prompt(
    sales_csv: str,
    inventory_csv: str,
    raw_materials_csv: str,
    bom_csv: str,
    events_csv: Optional[str] = None,
) -> str:
    events_block = events_csv or ""
    prompt = f"""
    You are given CSV data for a meat factory.

    sales_history.csv:
    - Columns: date, sku, units_sold
    {sales_csv}

    inventory.csv:
    - Columns: sku, units_in_stock, expiry_date
    {inventory_csv}

    raw_materials.csv:
    - Columns: material_id, units_in_stock, expiry_date
    {raw_materials_csv}

    bill_of_materials.csv:
    - Columns: sku, material_id, quantity_needed_per_unit
    {bom_csv}

    events.csv (optional):
    - Columns: date, description
    {events_block}

    Tasks:
    1) Analyze sales trends per SKU (increasing, decreasing, or stable) and estimate next week's demand.
       - Compute average daily sales and project forward 7 days.
       - Adjust for observable trends in the recent days.
       - If events are provided, reasonably adjust forecasts for relevant SKUs.
    2) Develop a production plan per SKU using:
       suggested_production = max(0, forecasted_demand - current_inventory)
    3) Determine raw material needs:
       - For each SKU in the production plan, multiply suggested_production by the BOM quantities, then sum by material_id.
       - Compare needed quantities against raw_materials current stock to compute suggested orders.
    4) Identify risks:
       - Expiry risks for items expiring within the next 3–7 days (both finished goods and raw materials).
       - Potential stockouts based on forecast vs inventory.
    5) Generate a concise, manager-friendly summary of key findings and recommendations.

    Output requirements:
    - Return ONLY one valid JSON object with exactly these keys and structures, no extra text:
    {{
      "forecast_table": [
        {{"sku": "string", "forecasted_demand": "integer", "confidence_or_reason": "string"}}
      ],
      "production_plan": [
        {{"sku": "string", "forecasted_demand": "integer", "current_inventory": "integer", "suggested_production": "integer"}}
      ],
      "raw_material_orders": [
        {{"material_id": "string", "needed_qty_kg": "integer", "current_stock_kg": "integer", "suggested_order_kg": "integer"}}
      ],
      "risk_alerts": [
        {{"alert_type": "string", "description": "string", "sku_or_material": "string"}}
      ],
      "summary_text": "string"
    }}
    - Use integers for all quantities where indicated. Round sensibly when needed.
    - Do not include explanations outside the JSON.
    """
    return dedent(prompt).strip()
