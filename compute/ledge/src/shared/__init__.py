"""Shared module for Ledge."""

from .constants import (
    QueueSuffix,
    TaskName,
    TASK_QUEUE_CPU,
    TASK_QUEUE_GPU,
    GPU_TASKS,
    CPU_TASKS,
    DEFAULT_PORTS,
    NAT_RULES,
    MODEL_PATHS,
    RUNTIME_LIMITS,
)
from .models import (
    STTRequest,
    STTResponse,
    TranscribeWorkflowInput,
    TTSRequest,
    TTSResponse,
    LLMRequest,
    LLMResponse,
    VoiceWorkflowInput,
    VoiceWorkflowOutput,
    HealthResponse,
    WorkflowTriggerRequest,
    WorkflowTriggerResponse,
)
from .logger import logger, get_logger, setup_logger


def __getattr__(name: str):
    """Lazily import config symbols to avoid workflow sandbox side effects."""
    if name in {"settings", "get_settings", "Settings"}:
        from .config import settings, get_settings, Settings

        mapping = {
            "settings": settings,
            "get_settings": get_settings,
            "Settings": Settings,
        }
        return mapping[name]
    raise AttributeError(f"module 'src.shared' has no attribute '{name}'")

__all__ = [
    "settings",
    "get_settings",
    "Settings",
    "QueueSuffix",
    "TaskName",
    "TASK_QUEUE_CPU",
    "TASK_QUEUE_GPU",
    "GPU_TASKS",
    "CPU_TASKS",
    "DEFAULT_PORTS",
    "NAT_RULES",
    "MODEL_PATHS",
    "RUNTIME_LIMITS",
    "STTRequest",
    "STTResponse",
    "TranscribeWorkflowInput",
    "TTSRequest",
    "TTSResponse",
    "LLMRequest",
    "LLMResponse",
    "VoiceWorkflowInput",
    "VoiceWorkflowOutput",
    "HealthResponse",
    "WorkflowTriggerRequest",
    "WorkflowTriggerResponse",
    "logger",
    "get_logger",
    "setup_logger",
]
