"""MinIO auth resolution helpers shared by services and scripts."""

from __future__ import annotations

import os
from pathlib import Path

from src.shared.config import settings


def _looks_placeholder(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("${") and stripped.endswith("}")


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_env_file(env_file: str) -> dict[str, str]:
    path = Path(env_file)
    try:
        if not path.exists() or not path.is_file():
            return {}
    except OSError:
        return {}

    data: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def resolve_minio_auth() -> tuple[str, str, str, bool]:
    """Resolve MinIO endpoint and credentials with deterministic precedence."""
    env_file = os.getenv("LEDGE_MINIO_ENV_FILE", "/etc/ledge/minio.env")
    env_values = _read_env_file(env_file)

    endpoint = os.getenv("MINIO_ENDPOINT") or env_values.get("MINIO_ENDPOINT") or settings.minio.endpoint

    secure_default = settings.minio.secure
    if "MINIO_SECURE" in env_values:
        secure_default = env_values["MINIO_SECURE"].strip().lower() in {"1", "true", "yes", "on"}
    secure = _bool_env("MINIO_SECURE", secure_default)

    access_key = os.getenv("MINIO_ACCESS_KEY", "")
    secret_key = os.getenv("MINIO_SECRET_KEY", "")

    if not access_key:
        access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    if not secret_key:
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "") or os.getenv("AWS_SECRET_KEY_ID", "")

    if not access_key:
        access_key = env_values.get("MINIO_ACCESS_KEY", "")
    if not secret_key:
        secret_key = env_values.get("MINIO_SECRET_KEY", "")

    if not access_key and settings.minio.access_key and not _looks_placeholder(settings.minio.access_key):
        access_key = settings.minio.access_key
    if not secret_key and settings.minio.secret_key and not _looks_placeholder(settings.minio.secret_key):
        secret_key = settings.minio.secret_key

    if not access_key or not secret_key:
        raise RuntimeError("MINIO_ACCESS_KEY/MINIO_SECRET_KEY are required")

    return endpoint, access_key, secret_key, secure


def has_minio_auth() -> bool:
    try:
        resolve_minio_auth()
        return True
    except Exception:
        return False


def create_minio_client():
    from minio import Minio

    endpoint, access_key, secret_key, secure = resolve_minio_auth()
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
