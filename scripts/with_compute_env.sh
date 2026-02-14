#!/usr/bin/env bash
set -euo pipefail

# Compute-side safe defaults for split-host deployment.
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-64.229.113.233:7233}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-64.229.113.233:9000}"
export MINIO_SECURE="${MINIO_SECURE:-false}"

# Fallback source for template environments that only expose values to PID 1.
read_pid1_env() {
  local key="$1"
  if [ ! -r /proc/1/environ ]; then
    return 1
  fi
  tr '\0' '\n' < /proc/1/environ | sed -n "s/^${key}=//p" | head -n 1
}

# Prefer explicit MinIO vars; then AWS aliases; then PID 1 inherited env.
if [ -z "${MINIO_ACCESS_KEY:-}" ]; then
  if [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
    export MINIO_ACCESS_KEY="${AWS_ACCESS_KEY_ID}"
  else
    pid1_access="$(read_pid1_env MINIO_ACCESS_KEY || true)"
    if [ -n "${pid1_access:-}" ]; then
      export MINIO_ACCESS_KEY="$pid1_access"
    fi
  fi
fi
if [ -z "${MINIO_SECRET_KEY:-}" ]; then
  if [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    export MINIO_SECRET_KEY="${AWS_SECRET_ACCESS_KEY}"
  elif [ -n "${AWS_SECRET_KEY_ID:-}" ]; then
    export MINIO_SECRET_KEY="${AWS_SECRET_KEY_ID}"
  else
    pid1_secret="$(read_pid1_env MINIO_SECRET_KEY || true)"
    if [ -n "${pid1_secret:-}" ]; then
      export MINIO_SECRET_KEY="$pid1_secret"
    fi
  fi
fi

# Keep AWS aliases in sync for code paths using either name.
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${MINIO_ACCESS_KEY:-}}"
if [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_KEY_ID:-${MINIO_SECRET_KEY:-}}"
fi

# Avoid silently using wrong defaults on GPU instance.
if [ -z "${MINIO_ACCESS_KEY:-}" ] || [ -z "${MINIO_SECRET_KEY:-}" ]; then
  echo "[with_compute_env] ERROR: missing MINIO_ACCESS_KEY/MINIO_SECRET_KEY (or AWS aliases)" >&2
  exit 1
fi

exec "$@"
