from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from temporalio.client import Client
from src.backend.workflows import (
    VideoProcessingWorkflow,
    BatchProcessingWorkflow,
)
from src.api.routers import transcriptions
import re
import uuid
try:
    from pypinyin import lazy_pinyin
except Exception:  # pragma: no cover - optional fallback
    lazy_pinyin = None

app = FastAPI()

# Include routers
app.include_router(transcriptions.router)


class ProcessRequest(BaseModel):
    url: str


class BatchRequest(BaseModel):
    query: str
    limit: int = 10
    parallelism: int | None = None
    max_duration_minutes: int | None = None


def _resolve_batch_parallelism(limit: int, requested: int | None) -> int:
    if requested is not None:
        return max(1, min(4, int(requested)))
    if limit <= 2:
        return 1
    if limit <= 5:
        return 2
    if limit <= 10:
        return 3
    return 4


def _resolve_max_duration_minutes(requested: int | None) -> int:
    # Keep a practical clamp range.
    if requested is None:
        return 10
    return max(1, min(180, int(requested)))


def _safe_query_slug(query: str) -> str:
    raw = (query or "").strip()
    if not raw:
        return "batch"

    candidate = raw
    if lazy_pinyin is not None:
        try:
            pinyin = "".join(lazy_pinyin(raw))
            if pinyin.strip():
                candidate = pinyin
        except Exception:
            pass

    candidate = candidate.lower()
    candidate = re.sub(r"\s+", "-", candidate)
    candidate = re.sub(r"[^a-z0-9\-_]", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_-")
    return candidate or "batch"


@app.post("/process")
async def process_video(request: ProcessRequest):
    try:
        client = await Client.connect("localhost:7233")

        video_id = request.url.split('=')[-1] if '=' in request.url else request.url[-12:]
        handle = await client.start_workflow(
            VideoProcessingWorkflow.run,
            request.url,
            id=f"video-{video_id}",
            task_queue="video-processing-queue",
        )

        return {"status": "started", "workflow_id": handle.id, "run_id": handle.run_id}
    except Exception as e:
        print(f"Error starting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch")
async def batch_process(request: BatchRequest):
    try:
        client = await Client.connect("localhost:7233")

        parallelism = _resolve_batch_parallelism(request.limit, request.parallelism)
        max_duration_minutes = _resolve_max_duration_minutes(request.max_duration_minutes)
        request_id = str(uuid.uuid4())
        query_slug = _safe_query_slug(request.query)
        workflow_id = f"batch-{query_slug}-{request_id[:12]}"

        handle = await client.start_workflow(
            BatchProcessingWorkflow.run,
            (request.query, request.limit, parallelism, max_duration_minutes),
            id=workflow_id,
            task_queue="video-processing-queue",
        )

        return {
            "status": "started",
            "workflow_id": handle.id,
            "run_id": handle.run_id,
            "request_id": request_id,
            "parallelism": parallelism,
            "max_duration_minutes": max_duration_minutes,
        }

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
        "minio": "unknown",
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
        status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
