#!/usr/bin/env bash
set -euo pipefail

# Compute-side safe defaults for split-host deployment.
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-64.229.113.233:7233}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-64.229.113.233:9000}"
export MINIO_SECURE="${MINIO_SECURE:-false}"

# Prefer explicit MinIO vars; fall back to AWS aliases if provided.
if [ -z "${MINIO_ACCESS_KEY:-}" ]; then
  export MINIO_ACCESS_KEY="${AWS_ACCESS_KEY_ID:-minioadmin}"
fi
if [ -z "${MINIO_SECRET_KEY:-}" ]; then
  if [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    export MINIO_SECRET_KEY="${AWS_SECRET_ACCESS_KEY}"
  else
    export MINIO_SECRET_KEY="${AWS_SECRET_KEY_ID:-minioadmin}"
  fi
fi

# Keep AWS aliases in sync for code paths using either name.
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-$MINIO_ACCESS_KEY}"
if [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_KEY_ID:-$MINIO_SECRET_KEY}"
fi

exec "$@"
