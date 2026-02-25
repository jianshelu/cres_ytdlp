"""Shared configuration management for Ledge."""

import json
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class TemporalConfig(BaseModel):
    host: str = "192.168.2.140"
    port: int = 7233
    namespace: str = "ledge-repo"
    task_queue_cpu: str = "ledge-cpu"
    task_queue_gpu: str = "ledge-gpu"
    public_host: Optional[str] = "64.229.113.233"
    public_port: int = 7233

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def public_endpoint(self) -> str:
        return f"{self.public_host}:{self.public_port}"


class MinioConfig(BaseModel):
    endpoint: str = "192.168.2.140:9000"
    public_endpoint: str = "64.229.113.233:9000"
    access_key: str = ""
    secret_key: str = ""
    secure: bool = False
    bucket_audio: str = "ledge-repo"
    bucket_models: str = "ledge-repo"
    bucket_output: str = "ledge-repo"


class ModelConfig(BaseModel):
    path: str
    type: Optional[str] = None
    size: Optional[str] = None
    model: Optional[str] = None
    exists_check: bool = True


class ModelsConfig(BaseModel):
    llm: Optional[ModelConfig] = None
    whisper: Optional[ModelConfig] = None
    tts: Optional[ModelConfig] = None


class InstanceConfig(BaseModel):
    host: str = ""
    port: int = 22
    user: str = "root"
    ssh_key: str = "~/.ssh/id_iris92vastai"
    remote_path: str = "/workspace/ledge-repo"
    last_updated: Optional[str] = None
    notes: Optional[str] = None


class Settings(BaseSettings):
    app_name: str = "ledge"
    debug: bool = False
    log_level: str = "INFO"
    
    temporal: TemporalConfig = TemporalConfig()
    minio: MinioConfig = MinioConfig()
    models: ModelsConfig = ModelsConfig()
    instance: InstanceConfig = InstanceConfig()

    class Config:
        env_prefix = "LEDGE_"


def load_yaml_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_instance_config(instance_path: str = "instance.json") -> InstanceConfig:
    path = Path(instance_path)
    if not path.exists():
        return InstanceConfig()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return InstanceConfig(**data)


def get_settings() -> Settings:
    settings = Settings()
    
    temporal_yaml = load_yaml_config("configs/temporal.yaml")
    if temporal_yaml:
        temporal_data = temporal_yaml.get("temporal", {})
        settings.temporal = TemporalConfig(
            host=temporal_data.get("host", settings.temporal.host),
            port=temporal_data.get("port", settings.temporal.port),
            namespace=temporal_data.get("namespace", settings.temporal.namespace),
            task_queue_cpu=temporal_data.get("task_queue", {}).get("cpu", settings.temporal.task_queue_cpu),
            task_queue_gpu=temporal_data.get("task_queue", {}).get("gpu", settings.temporal.task_queue_gpu),
            public_host=temporal_data.get("public", {}).get("host", settings.temporal.public_host),
            public_port=temporal_data.get("public", {}).get("port", settings.temporal.public_port),
        )
    
    minio_yaml = load_yaml_config("configs/minio.yaml")
    if minio_yaml:
        minio_data = minio_yaml.get("minio", {})
        settings.minio = MinioConfig(
            endpoint=minio_data.get("endpoint", settings.minio.endpoint),
            public_endpoint=minio_data.get("public_endpoint", settings.minio.public_endpoint),
            access_key=minio_data.get("access_key", settings.minio.access_key),
            secret_key=minio_data.get("secret_key", settings.minio.secret_key),
            secure=minio_data.get("secure", settings.minio.secure),
            bucket_audio=minio_data.get("buckets", {}).get("audio", settings.minio.bucket_audio),
            bucket_models=minio_data.get("buckets", {}).get("models", settings.minio.bucket_models),
            bucket_output=minio_data.get("buckets", {}).get("output", settings.minio.bucket_output),
        )
    
    models_yaml = load_yaml_config("configs/models.yaml")
    if models_yaml:
        models_data = models_yaml.get("models", {})
        settings.models = ModelsConfig(
            llm=ModelConfig(**models_data.get("llm", {})) if models_data.get("llm") else None,
            whisper=ModelConfig(**models_data.get("whisper", {})) if models_data.get("whisper") else None,
            tts=ModelConfig(**models_data.get("tts", {})) if models_data.get("tts") else None,
        )
    
    settings.instance = load_instance_config()
    
    return settings


settings = get_settings()
