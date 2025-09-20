import os
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv

# Load environment variables from .env as early as possible (before importing routers/services)
load_dotenv()

from app.routers.analyze import router as analyze_router
from app.routers import chat as chat_router
from db import engine, Base
import models as db_models
from app.tools.risk_sentry import get_risks, post_briefing

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Environment already loaded above via load_dotenv()
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")

app = FastAPI(title="food-copilot-backend", version="0.1.0")

# CORS (allow all by default; adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(analyze_router)
app.include_router(chat_router.router, prefix="/chat")


# Ensure database tables exist at startup (helps in local/dev if init_db wasn't run)
@app.on_event("startup")
async def _init_db_on_startup():
    Base.metadata.create_all(bind=engine)

    # Start scheduler for Risk Sentry at 08:00 UTC daily
    tz = pytz.UTC
    scheduler = BackgroundScheduler(timezone=tz)

    def _daily_risk_job():
        try:
            risks = get_risks()
            post_briefing(risks.get("summary", "No summary"))
        except Exception as e:
            print(f"Risk Sentry failed: {e}")

    scheduler.add_job(_daily_risk_job, CronTrigger(hour=8, minute=0))
    scheduler.start()

    # Store scheduler on app state for later shutdown
    app.state._scheduler = scheduler


@app.on_event("shutdown")
async def _shutdown():
    sched = getattr(app.state, "_scheduler", None)
    if sched:
        try:
            sched.shutdown(wait=False)
        except Exception:
            pass


@app.get("/")
async def root():
    return {"status": "ok", "service": "food-copilot-backend"}


@app.get("/health")
async def health():
    """Basic health and AWS credentials status check.
    Returns service info, region, model id presence, and STS identity if available.
    """
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    info: Dict[str, Any] = {
        "status": "ok",
        "service": "food-copilot-backend",
        "aws_region": AWS_REGION,
        "bedrock_model_id_present": bool(BEDROCK_MODEL_ID),
        "bedrock_model_id": BEDROCK_MODEL_ID if BEDROCK_MODEL_ID else None,
        "aws": {
            "credentials_present": bool(os.getenv("AWS_ACCESS_KEY_ID") and (os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SESSION_TOKEN"))),
            "access_key_id_prefix": (os.getenv("AWS_ACCESS_KEY_ID") or "")[:4],
            "session_token_present": bool(os.getenv("AWS_SESSION_TOKEN")),
            "expiry_time": None,
            "sts_identity": None,
            "error": None,
        },
    }

    try:
        session = boto3.session.Session(region_name=AWS_REGION)
        creds = session.get_credentials()
        if creds is not None and hasattr(creds, "get_frozen_credentials"):
            expiry = getattr(creds, "expiry_time", None)
            if expiry is not None:
                try:
                    info["aws"]["expiry_time"] = expiry.isoformat() if hasattr(expiry, "isoformat") else str(expiry)
                except Exception:
                    info["aws"]["expiry_time"] = str(expiry)
        sts = session.client("sts")
        ident = sts.get_caller_identity()
        info["aws"]["sts_identity"] = {
            "account": ident.get("Account"),
            "arn": ident.get("Arn"),
            "user_id": ident.get("UserId"),
        }
    except ClientError as e:  # type: ignore
        code = e.response.get("Error", {}).get("Code") if hasattr(e, "response") else None
        info["aws"]["error"] = {"type": "ClientError", "code": code, "message": str(e)}
    except BotoCoreError as e:  # type: ignore
        info["aws"]["error"] = {"type": "BotoCoreError", "message": str(e)}
    except Exception as e:
        info["aws"]["error"] = {"type": "Exception", "message": str(e)}

    return info


# AWS Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
