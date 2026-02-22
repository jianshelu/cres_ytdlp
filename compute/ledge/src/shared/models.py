"""Pydantic models for Ledge."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _coerce_temporal_bytes(value):
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, list) and all(isinstance(item, int) for item in value):
        return bytes(value)
    return value


class STTRequest(BaseModel):
    audio_data: bytes
    language: Optional[str] = None
    model_size: str = "/workspace/packages/models/whisperx/faster-whisper-large-v2"

    @field_validator("audio_data", mode="before")
    @classmethod
    def normalize_audio_data(cls, value):
        return _coerce_temporal_bytes(value)


class STTResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float
    confidence: Optional[float] = None


class TTSRequest(BaseModel):
    text: str
    language: str = "zh"
    speaker: Optional[str] = None
    speed: float = 1.0


class TTSResponse(BaseModel):
    audio_data: bytes
    sample_rate: int
    duration_seconds: float

    @field_validator("audio_data", mode="before")
    @classmethod
    def normalize_audio_data(cls, value):
        return _coerce_temporal_bytes(value)


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7


class LLMResponse(BaseModel):
    text: str
    tokens_used: int
    finish_reason: str


class VoiceWorkflowInput(BaseModel):
    audio_data: bytes
    language: Optional[str] = None

    @field_validator("audio_data", mode="before")
    @classmethod
    def normalize_audio_data(cls, value):
        return _coerce_temporal_bytes(value)


class VoiceWorkflowOutput(BaseModel):
    transcribed_text: str
    llm_response: str
    audio_response: bytes
    total_duration_seconds: float

    @field_validator("audio_response", mode="before")
    @classmethod
    def normalize_audio_response(cls, value):
        return _coerce_temporal_bytes(value)


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str
    version: str = "0.1.0"
    checks: dict = Field(default_factory=dict)


class WorkflowTriggerRequest(BaseModel):
    workflow_type: str
    input_data: dict
    wait_for_result: bool = False
    timeout_seconds: int = 300


class WorkflowTriggerResponse(BaseModel):
    workflow_id: str
    status: str
    result: Optional[dict] = None
