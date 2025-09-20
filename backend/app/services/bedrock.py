import json
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Region and model id (ARN recommended)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID")

# Optional generation params
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
TOP_K = int(os.getenv("TOP_K", "250"))
BEDROCK_LATENCY = os.getenv("BEDROCK_LATENCY", "standard")


class BedrockClient:
    def __init__(self, model_id: 'str | None' = None, region: 'str | None' = None):
        # Resolve model and region; require model id to be set
        # Read BEDROCK_MODEL_ID from environment at initialization to avoid module import timing issues
        self.model_id = model_id if model_id is not None else os.getenv("BEDROCK_MODEL_ID")
        self.region = region or AWS_REGION
        if not self.model_id:
            raise RuntimeError("BEDROCK_MODEL_ID is not set")
        self._client = boto3.client("bedrock-runtime", region_name=self.region)

    def _refresh_client(self) -> None:
        # Recreate the boto3 client using a fresh Session (helps with SSO/assume-role refresh)
        session = boto3.session.Session(region_name=self.region)
        self._client = session.client("bedrock-runtime")

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Calls Bedrock Converse with system + user prompts and returns parsed JSON from the model output.
        If credentials are expired, refresh the client once and retry. Propagates errors to caller.
        """
        def _call():
            return self._client.converse(
                modelId=self.model_id,
                system=[{"text": system_prompt}] if system_prompt else [],
                messages=[{
                    "role": "user",
                    "content": [{"text": user_prompt}],
                }],
                inferenceConfig={
                    "maxTokens": MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "topP": TOP_P,
                },
                additionalModelRequestFields={
                    "top_k": TOP_K,
                },
            )

        try:
            resp = _call()
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code") if hasattr(e, "response") else None
            if code in {"ExpiredToken", "ExpiredTokenException"}:
                self._refresh_client()
                resp = _call()
            else:
                raise
        except BotoCoreError:
            # Retry once on generic botocore transport error
            self._refresh_client()
            resp = _call()

        # Extract text from the response and parse JSON
        content = resp.get("output", {}).get("message", {}).get("content", [])
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and "text" in part]
        text = "".join(text_parts).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Propagate parsing errors so caller can handle
            raise e

    @staticmethod
    def _mock_response() -> Dict[str, Any]:
        # Kept only for backward compatibility with the router check; not used anymore.
        return {
            "forecast_table": [
                {"sku": "sausages_1kg", "forecasted_demand": 1400, "confidence_or_reason": "trend up 12%"},
                {"sku": "chicken_breast", "forecasted_demand": 900, "confidence_or_reason": "stable demand"},
            ],
            "production_plan": [
                {"sku": "sausages_1kg", "forecasted_demand": 1400, "current_inventory": 600, "suggested_production": 800},
                {"sku": "chicken_breast", "forecasted_demand": 900, "current_inventory": 400, "suggested_production": 500},
            ],
            "raw_material_orders": [
                {"material_id": "pork_loins", "needed_qty_kg": 2500, "current_stock_kg": 2000, "suggested_order_kg": 500}
            ],
            "risk_alerts": [
                {"alert_type": "expiry", "description": "200 sausages expire in 3 days", "sku_or_material": "sausages_1kg"}
            ],
            "summary_text": "Demand for sausages is rising due to BBQ season. Recommend producing 800 more and ordering 500kg of pork.",
        }
