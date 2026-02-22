"""Compute API - FastAPI service on GPU node (port 8100)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.shared import get_logger

logger = get_logger("compute_api")

app = FastAPI(
    title="Ledge Compute API",
    description="Compute plane API for GPU inference (STT, TTS, LLM)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routes import health, stt, tts

app.include_router(health.router, tags=["health"])
app.include_router(stt.router, prefix="/stt", tags=["stt"])
app.include_router(tts.router, prefix="/tts", tags=["tts"])


@app.on_event("startup")
async def startup_event():
    logger.info("Compute API starting")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Compute API shutting down")
