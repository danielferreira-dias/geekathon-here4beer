from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import sys
import os
from typing import AsyncGenerator
from app.models.query_schema import QueryRequest, QueryResponse

# Add the services directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
from agent_here4beer import query_with_memory

app = FastAPI(title="Food Provider Agent API", version="1.0.0")



@app.get("/")
async def root():
    return {"message": "Food Provider Agent API is running"}

@app.post("/query")
async def query_agent(request: QueryRequest):
    """Query the food provider agent"""
    try:
        response = query_with_memory(request.message)
        return QueryResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/stream")
async def query_agent_stream(request: QueryRequest):
    """Query the food provider agent with streaming response"""

    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # Get the response from the agent
            response = query_with_memory(request.message)

            # Split response into chunks for streaming effect
            words = response.split()
            for i, word in enumerate(words):
                chunk = {
                    "type": "token",
                    "content": word + (" " if i < len(words) - 1 else ""),
                    "is_final": i == len(words) - 1
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            # Send final completion signal
            final_chunk = {
                "type": "completion",
                "content": "",
                "is_final": True
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"

        except Exception as e:
            error_chunk = {
                "type": "error",
                "content": str(e),
                "is_final": True
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "food-provider-agent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)