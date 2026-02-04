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
        handle = await client.start_workflow(
            VideoProcessingWorkflow.run,
            request.url,
            id=f"video-{request.url}", # Simple ID deduplication
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
        client = await Client.connect("localhost:7233")
        
        import uuid
        handle = await client.start_workflow(
            BatchProcessingWorkflow.run,
            (request.query, request.limit),
            id=f"batch-{uuid.uuid4()}",
            task_queue="video-processing-queue",
        )
        return {"status": "started", "workflow_id": handle.id, "run_id": handle.run_id}
        
    except Exception as e:
        print(f"Error starting batch workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
