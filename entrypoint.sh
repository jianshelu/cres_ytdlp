#!/usr/bin/env bash
set -euo pipefail

cd /workspace

mkdir -p /workspace/logs /workspace/run /workspace/scripts

PROJECT_PROFILE="${PROJECT_PROFILE:-cres}"
case "${PROJECT_PROFILE}" in
  cres)
    default_project_root="/workspace"
    default_supervisord_config="/etc/supervisor/supervisord.cres.conf"
    default_api_role="compute"
    ;;
  ledge)
    default_project_root="/workspace/ledge-repo"
    default_supervisord_config="/etc/supervisor/supervisord.ledge.conf"
    default_api_role="compute"
    ;;
  *)
    echo "[entrypoint] unsupported PROJECT_PROFILE=${PROJECT_PROFILE} (expected: cres|ledge)" >&2
    exit 1
    ;;
esac

export PROJECT_ROOT="${PROJECT_ROOT:-${default_project_root}}"
SUPERVISORD_CONFIG="${SUPERVISORD_CONFIG:-${default_supervisord_config}}"

# Safe defaults for compute-node style runtime.
export PYTHONPATH="${PYTHONPATH:-${PROJECT_ROOT}}"
export API_ROLE="${API_ROLE:-${default_api_role}}"
export AUTO_REINDEX_ON_START="${AUTO_REINDEX_ON_START:-false}"
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-64.229.113.233:7233}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-64.229.113.233:9000}"
export MINIO_SECURE="${MINIO_SECURE:-false}"

# CI/no-GPU hosts can opt out cleanly; runtime can override.
export WORKER_GPU_OPTIONAL="${WORKER_GPU_OPTIONAL:-1}"
export LLAMA_DISABLE="${LLAMA_DISABLE:-0}"

SUPERVISORD_BIN="$(command -v supervisord || true)"
if [ -z "${SUPERVISORD_BIN}" ]; then
  echo "[entrypoint] supervisord not found in PATH" >&2
  exit 1
fi

if [ ! -f "${SUPERVISORD_CONFIG}" ]; then
  echo "[entrypoint] missing ${SUPERVISORD_CONFIG}" >&2
  exit 1
fi

if [ ! -d "${PROJECT_ROOT}" ]; then
  echo "[entrypoint] missing PROJECT_ROOT=${PROJECT_ROOT}" >&2
  exit 1
fi

ln -sf "${SUPERVISORD_CONFIG}" /etc/supervisor/supervisord.conf

exec "${SUPERVISORD_BIN}" -n -c "${SUPERVISORD_CONFIG}"
