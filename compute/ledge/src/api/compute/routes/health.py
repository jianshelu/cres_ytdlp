"""Health check endpoint for Compute API."""

import subprocess

from fastapi import APIRouter

from src.shared import HealthResponse, RUNTIME_LIMITS

router = APIRouter()


def check_gpu() -> dict:
    """Check GPU availability."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.free", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return {"available": True, "info": result.stdout.strip()}
        return {"available": False, "error": result.stderr}
    except Exception as e:
        return {"available": False, "error": str(e)}


def check_llama() -> dict:
    """Check llama.cpp availability."""
    import httpx
    try:
        response = httpx.get("http://127.0.0.1:8081/health", timeout=2.0)
        return {"available": response.status_code == 200}
    except Exception as e:
        return {"available": False, "error": str(e)}


def check_whisper_model() -> dict:
    """Check Whisper model exists."""
    from pathlib import Path
    whisper_path = Path("/workspace/packages/models/whisperx")
    return {"available": whisper_path.exists(), "path": str(whisper_path)}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check with GPU and service status."""
    return HealthResponse(
        status="healthy",
        service="compute-api",
        checks={
            "gpu": check_gpu(),
            "llama": check_llama(),
            "whisper_model": check_whisper_model(),
            "runtime_limits": RUNTIME_LIMITS,
        },
    )


@router.get("/")
async def root():
    """Root endpoint."""
    return {"service": "compute-api", "status": "running"}
