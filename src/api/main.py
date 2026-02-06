from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from temporalio.client import Client
from src.backend.workflows import VideoProcessingWorkflow, BatchProcessingWorkflow
import os

app = FastAPI()

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
    return {"status": "ok"}
