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
import os
import sys
import asyncio
import subprocess
from pathlib import Path
try:
    from pypinyin import lazy_pinyin
except Exception:  # pragma: no cover - optional fallback
    lazy_pinyin = None

app = FastAPI()

# Include routers
app.include_router(transcriptions.router)

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
BASE_TASK_QUEUE = os.getenv("BASE_TASK_QUEUE", "video-processing").strip() or "video-processing"
CPU_TASK_QUEUE = f"{BASE_TASK_QUEUE}@cpu"
LLAMA_HEALTH_URL = os.getenv("LLAMA_HEALTH_URL", "http://localhost:8081/health")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}
AUTO_REINDEX_ENABLED = os.getenv("AUTO_REINDEX_ENABLED", "false").lower() in {"1", "true", "yes"}
AUTO_REINDEX_INTERVAL_SECONDS = max(15, int(os.getenv("AUTO_REINDEX_INTERVAL_SECONDS", "45")))
AUTO_REINDEX_ON_START = os.getenv("AUTO_REINDEX_ON_START", "true").lower() in {"1", "true", "yes"}
AUTO_START_WORKERS_ON_BATCH = os.getenv("AUTO_START_WORKERS_ON_BATCH", "true").lower() in {"1", "true", "yes"}
SCHEDULER_ACTIVE_INSTANCE = os.getenv("SCHEDULER_ACTIVE_INSTANCE", "true").lower() in {"1", "true", "yes"}
SCHEDULER_ACTIVE_MAX_PARALLELISM = max(1, int(os.getenv("SCHEDULER_ACTIVE_MAX_PARALLELISM", "2")))
DEFAULT_YOUTUBE_CATEGORY = os.getenv("YOUTUBE_DEFAULT_CATEGORY", "Science & Technology").strip() or "Science & Technology"
_reindex_task: asyncio.Task | None = None
_reindex_lock = asyncio.Lock()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_index_rebuild_sync() -> str:
    root = _project_root()
    script_path = root / "generate_index.py"
    if not script_path.exists():
        raise RuntimeError(f"generate_index.py not found: {script_path}")

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    return (proc.stdout or proc.stderr or "index rebuilt").strip()


def _start_workers_best_effort_sync() -> str:
    """
    Best-effort on-demand worker start for single-host deployments.
    In split-host mode (API not colocated with supervisor), this safely no-ops.
    """
    cmds = [
        ["supervisorctl", "-s", "unix:///tmp/supervisor.sock", "start", "worker-cpu"],
        ["supervisorctl", "-s", "unix:///tmp/supervisor.sock", "start", "worker-gpu"],
    ]
    lines = []
    for cmd in cmds:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            out = (proc.stdout or proc.stderr or "").strip()
            lines.append(out or f"{cmd[-1]}: no output")
        except Exception as e:
            lines.append(f"{cmd[-1]}: skipped ({e})")
    return " | ".join(lines)


async def _maybe_start_workers_on_demand() -> None:
    if not AUTO_START_WORKERS_ON_BATCH:
        return
    try:
        result = await asyncio.to_thread(_start_workers_best_effort_sync)
        print(f"[worker-autostart] {result}")
    except Exception as e:
        print(f"[worker-autostart] skipped: {e}")


async def _rebuild_index_once() -> str:
    async with _reindex_lock:
        return await asyncio.to_thread(_run_index_rebuild_sync)


async def _auto_reindex_loop() -> None:
    while True:
        try:
            await _rebuild_index_once()
        except Exception as e:
            print(f"[auto-reindex] failed: {e}")
        await asyncio.sleep(AUTO_REINDEX_INTERVAL_SECONDS)


def _minio_health_url() -> str:
    scheme = "https" if MINIO_SECURE else "http"
    return f"{scheme}://{MINIO_ENDPOINT}/minio/health/live"


class ProcessRequest(BaseModel):
    url: str


class BatchRequest(BaseModel):
    query: str
    limit: int = 10
    parallelism: int | None = None
    max_duration_minutes: int | None = None
    youtube_category: str = DEFAULT_YOUTUBE_CATEGORY


def _resolve_batch_parallelism(limit: int, requested: int | None) -> int:
    gpu_threads = max(1, int(os.getenv("WORKER_GPU_THREADS", "2")))
    cpu_threads = max(1, int(os.getenv("WORKER_CPU_THREADS", "4")))
    thread_cap = max(1, min(gpu_threads, cpu_threads))
    hard_cap = min(4, thread_cap)
    if SCHEDULER_ACTIVE_INSTANCE:
        hard_cap = min(hard_cap, SCHEDULER_ACTIVE_MAX_PARALLELISM)

    if requested is not None:
        return max(1, min(hard_cap, int(requested)))

    if limit <= 2:
        resolved = 1
    elif limit <= 5:
        resolved = 2
    elif limit <= 10:
        resolved = 3
    else:
        resolved = 4

    return max(1, min(hard_cap, resolved))


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


@app.on_event("startup")
async def _startup_tasks():
    global _reindex_task
    if AUTO_REINDEX_ON_START:
        try:
            await _rebuild_index_once()
        except Exception as e:
            print(f"[auto-reindex] startup rebuild failed: {e}")

    if AUTO_REINDEX_ENABLED and _reindex_task is None:
        _reindex_task = asyncio.create_task(_auto_reindex_loop())


@app.on_event("shutdown")
async def _shutdown_tasks():
    global _reindex_task
    if _reindex_task:
        _reindex_task.cancel()
        try:
            await _reindex_task
        except asyncio.CancelledError:
            pass
        _reindex_task = None


@app.post("/process")
async def process_video(request: ProcessRequest):
    try:
        await _maybe_start_workers_on_demand()
        client = await Client.connect(TEMPORAL_ADDRESS)

        video_id = request.url.split('=')[-1] if '=' in request.url else request.url[-12:]
        handle = await client.start_workflow(
            VideoProcessingWorkflow.run,
            request.url,
            id=f"video-{video_id}",
            task_queue=CPU_TASK_QUEUE,
        )

        return {"status": "started", "workflow_id": handle.id, "run_id": handle.run_id}
    except Exception as e:
        print(f"Error starting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch")
async def batch_process(request: BatchRequest):
    try:
        await _maybe_start_workers_on_demand()
        client = await Client.connect(TEMPORAL_ADDRESS)

        parallelism = _resolve_batch_parallelism(request.limit, request.parallelism)
        max_duration_minutes = _resolve_max_duration_minutes(request.max_duration_minutes)
        youtube_category = (request.youtube_category or DEFAULT_YOUTUBE_CATEGORY).strip() or DEFAULT_YOUTUBE_CATEGORY
        request_id = str(uuid.uuid4())
        query_slug = _safe_query_slug(request.query)
        workflow_id = f"batch-{query_slug}-{request_id[:12]}"

        handle = await client.start_workflow(
            BatchProcessingWorkflow.run,
            (request.query, request.limit, parallelism, max_duration_minutes, youtube_category),
            id=workflow_id,
            task_queue=CPU_TASK_QUEUE,
        )

        return {
            "status": "started",
            "workflow_id": handle.id,
            "run_id": handle.run_id,
            "request_id": request_id,
            "parallelism": parallelism,
            "max_duration_minutes": max_duration_minutes,
            "youtube_category": youtube_category,
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
            resp = await client.get(LLAMA_HEALTH_URL)
            checks["llama"] = "ok" if resp.status_code == 200 else "down"
    except Exception:
        checks["llama"] = "down"

    # Check Temporal via gRPC connection test.
    try:
        await Client.connect(TEMPORAL_ADDRESS)
        checks["temporal"] = "ok"
    except Exception:
        checks["temporal"] = "down"

    # Check MinIO endpoint.
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(_minio_health_url())
            checks["minio"] = "ok" if resp.status_code == 200 else "down"
    except Exception:
        checks["minio"] = "down"

    all_healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content=checks,
        status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.post("/admin/reindex")
async def admin_reindex():
    try:
        result = await _rebuild_index_once()
        return {"status": "ok", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reindex failed: {e}")
