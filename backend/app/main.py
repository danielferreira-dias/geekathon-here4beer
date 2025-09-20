import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv

# Load environment variables from .env if present (for local/dev convenience)
load_dotenv()

from app.routers.analyze import router as analyze_router

app = FastAPI(title="food-copilot-backend", version="0.1.0")

# CORS (allow all by default; adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "food-copilot-backend"}


# AWS Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
