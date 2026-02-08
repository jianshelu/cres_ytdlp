from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from temporalio.client import Client
from src.backend.workflows import VideoProcessingWorkflow, BatchProcessingWorkflow
from src.api.routers import transcriptions
import os

app = FastAPI()

# Include routers
app.include_router(transcriptions.router)

class ProcessRequest(BaseModel):
    url: str

class BatchRequest(BaseModel):
    query: str
    limit: int = 10

@app.post("/process")
async def process_video(request: ProcessRequest):
    try:
        # Connect to Temporal
        # In Docker, this might be 'temporal' if using docker-compose, but we are in same container/net
        client = await Client.connect("localhost:7233")
        
        # Start Workflow
        video_id = request.url.split('=')[-1] if '=' in request.url else request.url[-12:]
        handle = await client.start_workflow(
            VideoProcessingWorkflow.run,
            request.url,
            id=f"video-{video_id}", # Standardized ID format
            task_queue="video-processing-queue",
        )
        
        return {"status": "started", "workflow_id": handle.id, "run_id": handle.run_id}
    except Exception as e:
        # Log the error
        print(f"Error starting workflow: {e}")
        # In a real app, handle connection errors (e.g., Temporal not ready) gracefully
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch")
async def batch_process(request: BatchRequest):
    try:
        from pypinyin import lazy_pinyin
        client = await Client.connect("localhost:7233")
        
        # Convert Chinese to Pinyin slug (e.g., "智能体" -> "zhinengti")
        pinyin_slug = "".join(lazy_pinyin(request.query))
        workflow_id = f"batch-{pinyin_slug}" if pinyin_slug else f"batch-{uuid.uuid4()}"
        
        handle = await client.start_workflow(
            BatchProcessingWorkflow.run,
            (request.query, request.limit),
            id=workflow_id,
            task_queue="video-processing-queue",
        )
        return {"status": "started", "workflow_id": handle.id, "run_id": handle.run_id}
        
    except Exception as e:
        print(f"Error starting batch workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """
    Comprehensive health check that verifies all critical dependencies.
    Returns 200 if all services are healthy, 503 if any are down.
    """
    import httpx
    from fastapi import status
    from fastapi.responses import JSONResponse
    
    checks = {
        "api": "ok",
        "llama": "unknown",
        "temporal": "unknown",
        "minio": "unknown"
    }
    
    # Check llama-server (port 8081)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:8081/health")
            checks["llama"] = "ok" if resp.status_code == 200 else "down"
    except Exception:
        checks["llama"] = "down"
    
    # Check Temporal (port 8233 UI API)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:8233/api/v1/namespaces")
            checks["temporal"] = "ok" if resp.status_code == 200 else "down"
    except Exception:
        checks["temporal"] = "down"
    
    # Check MinIO (port 9000 health endpoint)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:9000/minio/health/live")
            checks["minio"] = "ok" if resp.status_code == 200 else "down"
    except Exception:
        checks["minio"] = "down"
    
    all_healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content=checks,
        status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

