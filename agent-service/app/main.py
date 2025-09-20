from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import sys
import os
import json
import asyncio
from app.models.query_schema import QueryRequest, QueryResponse
# Add the services directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
from agent_here4beer import agent_instance

app = FastAPI(title="Food Provider Agent API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Food Provider Agent API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "food-provider-agent"}

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """Normal query route that returns agent response"""
    try:
        response = agent_instance.query_with_memory(request.message)
        return QueryResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/query/stream")
async def stream_agent_query(request: QueryRequest):
    """Streaming route for agent responses"""
    try:
        async def generate_response():
            # Get the full response from agent
            response = agent_instance.query_with_memory(request.message)

            # Stream the response word by word
            words = response.split()
            for i, word in enumerate(words):
                chunk = {
                    "content": word + " " if i < len(words) - 1 else word,
                    "done": i == len(words) - 1
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.1)  # Small delay for streaming effect

            # Send final done signal
            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent streaming error: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)