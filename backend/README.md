# food-copilot-backend

FastAPI backend that accepts manufacturing data (sales, inventory, raw materials, BOM, events), crafts a structured prompt, calls AWS Bedrock (Claude Sonnet), and returns a strict JSON planning package.

## Features
- Endpoint: `POST /analyze`
- Accepts multipart/form-data with required files:
  - `sales_history` (CSV/XLSX)
  - `inventory` (CSV/XLSX)
  - `raw_materials` (CSV/XLSX)
  - `bill_of_materials` (CSV/XLSX)
  - `events` (CSV/XLSX, optional)
- Parses files with pandas and normalizes to CSV text
- Builds a deterministic prompt
- Calls Bedrock Claude Sonnet via `boto3` (with a safe mock fallback if AWS is not configured)
- Validates and returns a strict JSON schema

## Tech
- Python 3.11
- FastAPI + Uvicorn
- pandas, pydantic, python-multipart
- boto3, python-dotenv
- mangum (optional Lambda handler)

## Project Structure
```
app/
  main.py
  routers/analyze.py
  services/bedrock.py
  services/prompt.py
  utils/csv_utils.py
  schemas.py
```

## Setup (local)
1. Python 3.11 recommended (or use Docker below)
2. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy env example:
   ```bash
   cp .env.example .env
   ```
   Then set:
   - `AWS_REGION` or `AWS_DEFAULT_REGION` (e.g., `us-east-1`)
   - AWS credentials for local dev: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and if using temporary creds, `AWS_SESSION_TOKEN`
   - Optionally `MODEL_ID` to a Bedrock model or an Inference Profile ARN, for example:
     `arn:aws:bedrock:us-east-1:816308070251:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0`
   - Optional tuning: `MAX_TOKENS`, `TEMPERATURE`, `TOP_P`, `TOP_K`, `BEDROCK_LATENCY`

   Note: The app loads `.env` automatically on startup for local convenience. In production, prefer IAM roles or AWS profiles.

4. Run server:
   ```bash
   uvicorn app.main:app --reload
   ```

5. Test with curl (sample files):
   ```bash
   curl -X POST http://localhost:8000/analyze \
     -F "sales_history=@samples/sales_history.csv" \
     -F "inventory=@samples/inventory.csv" \
     -F "raw_materials=@samples/raw_materials.csv" \
     -F "bill_of_materials=@samples/bill_of_materials.csv"
   ```

## Docker
Build and run:
```bash
docker build -t food-copilot-backend .
 docker run --rm -p 8000:8000 --env-file .env food-copilot-backend
```

## Endpoint
- `POST /analyze`
  - Form fields: `sales_history`, `inventory`, `raw_materials`, `bill_of_materials`, optional `events`.
  - Returns JSON schema:
    ```json
    {
      "forecast_table": [
        {"sku": "sausages_1kg", "forecasted_demand": 1400, "confidence_or_reason": "trend up 12%"}
      ],
      "production_plan": [
        {"sku": "sausages_1kg", "forecasted_demand": 1400, "current_inventory": 600, "suggested_production": 800}
      ],
      "raw_material_orders": [
        {"material_id": "pork_loins", "needed_qty_kg": 2500, "current_stock_kg": 2000, "suggested_order_kg": 500}
      ],
      "risk_alerts": [
        {"alert_type": "expiry", "description": "200 sausages expire in 3 days", "sku_or_material": "sausages_1kg"}
      ],
      "summary_text": "..."
    }
    ```

## Notes
- If Bedrock returns non-JSON or wrong schema, API will respond 502 with validation error details.
- Excel parsing requires `openpyxl` (included).
