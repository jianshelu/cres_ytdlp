"""Constants for Ledge."""

from enum import Enum


class QueueSuffix(str, Enum):
    CPU = "@cpu"
    GPU = "@gpu"


class TaskName(str, Enum):
    STT_TRANSCRIBE = "stt_transcribe"
    TTS_SYNTHESIZE = "tts_synthesize"
    LLM_GENERATE = "llm_generate"
    IMAGE_GENERATE = "image_generate"
    VIDEO_GENERATE = "video_generate"
    METADATA_PROCESS = "metadata_process"
    RESULT_FORMAT = "result_format"


TASK_QUEUE_CPU = "ledge-cpu"
TASK_QUEUE_GPU = "ledge-gpu"


GPU_TASKS = {
    TaskName.STT_TRANSCRIBE: f"{TaskName.STT_TRANSCRIBE.value}{QueueSuffix.GPU.value}",
    TaskName.TTS_SYNTHESIZE: f"{TaskName.TTS_SYNTHESIZE.value}{QueueSuffix.GPU.value}",
    TaskName.LLM_GENERATE: f"{TaskName.LLM_GENERATE.value}{QueueSuffix.GPU.value}",
    TaskName.IMAGE_GENERATE: f"{TaskName.IMAGE_GENERATE.value}{QueueSuffix.GPU.value}",
    TaskName.VIDEO_GENERATE: f"{TaskName.VIDEO_GENERATE.value}{QueueSuffix.GPU.value}",
}

CPU_TASKS = {
    TaskName.METADATA_PROCESS: f"{TaskName.METADATA_PROCESS.value}{QueueSuffix.CPU.value}",
    TaskName.RESULT_FORMAT: f"{TaskName.RESULT_FORMAT.value}{QueueSuffix.CPU.value}",
}


DEFAULT_PORTS = {
    "control_api": 8100,
    "compute_api": 8100,
    "web_ui": 3100,
    "temporal": 7233,
    "minio": 9000,
    "llama": 8081,
}


NAT_RULES = {
    "temporal": {"private": "192.168.2.140:7233", "public": "64.229.113.233:7233"},
    "minio": {"private": "192.168.2.140:9000", "public": "64.229.113.233:9000"},
    "control_api": {"private": "192.168.2.140:8100", "public": "64.229.113.233:8100"},
    "web_ui": {"private": "192.168.2.140:3100", "public": None},
}


MODEL_PATHS = {
    "llm": "/workspace/packages/models/llm",
    "whisper": "/workspace/packages/models/whisperx",
    "tts": "/workspace/packages/models/tts",
}


RUNTIME_LIMITS = {
    "background_ram_gb": 7,
    "llama_ram_gb": 3,
    "workers_ram_gb": 4,
    "llama_offload": 999,
    "llama_batch": 512,
    "llama_threads": 8,
}
