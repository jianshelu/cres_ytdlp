#!/usr/bin/env bash
set -euo pipefail

# Defaults: model sync happens after deploy
LLM_MODEL_PATH="${LLM_MODEL_PATH:-/workspace/packages/models/llm}"
LLM_MODEL_FILE="${LLM_MODEL_FILE:-Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"

LLAMA_HOST="${LLAMA_HOST:-0.0.0.0}"
LLAMA_PORT="${LLAMA_PORT:-8081}"

# RTX 3060 12GB + 10 vCPU tuned defaults
LLAMA_THREADS="${LLAMA_THREADS:-8}"
LLAMA_CTX_SIZE="${LLAMA_CTX_SIZE:-4096}"
LLAMA_PARALLEL="${LLAMA_PARALLEL:-1}"
LLAMA_NGL="${LLAMA_NGL:-999}"

# Wait for model sync (supervisor retry-friendly)
LLAMA_WAIT_SECONDS="${LLAMA_WAIT_SECONDS:-1800}"   # 30 min
LLAMA_POLL_SECONDS="${LLAMA_POLL_SECONDS:-5}"

MODEL_FULL_PATH="${LLM_MODEL_PATH%/}/${LLM_MODEL_FILE}"

log() {
  echo "[llama] $*"
}

die() {
  log "ERROR: $*"
  exit 1
}

print_model_diagnostics() {
  log "Model path diagnostics for ${MODEL_FULL_PATH}:"
  ls -lah "${LLM_MODEL_PATH}" 2>/dev/null || true
  if [ -e "${MODEL_FULL_PATH}" ]; then
    stat -c '%n %F %s bytes mode=%a' "${MODEL_FULL_PATH}" 2>/dev/null || true
  else
    log "Expected model file not visible at ${MODEL_FULL_PATH}"
  fi
}

validate_model_path_state() {
  local listed_path
  listed_path="$(find "${LLM_MODEL_PATH}" -maxdepth 1 -type f -name "${LLM_MODEL_FILE}" -print -quit 2>/dev/null || true)"

  if [ -e "${MODEL_FULL_PATH}" ] && [ ! -f "${MODEL_FULL_PATH}" ]; then
    print_model_diagnostics
    die "Model path exists but is not a regular file"
  fi

  if [ -f "${MODEL_FULL_PATH}" ] && [ ! -r "${MODEL_FULL_PATH}" ]; then
    print_model_diagnostics
    die "Model file exists but is not readable"
  fi

  if [ -n "${listed_path}" ] && [ ! -e "${MODEL_FULL_PATH}" ]; then
    print_model_diagnostics
    die "Inconsistent exists state: directory scan sees model but direct path check reports missing"
  fi
}

if [ -e "${LLM_MODEL_PATH}" ] && [ ! -d "${LLM_MODEL_PATH}" ]; then
  die "LLM_MODEL_PATH exists but is not a directory: ${LLM_MODEL_PATH}"
fi
mkdir -p "${LLM_MODEL_PATH}"

write_probe="${LLM_MODEL_PATH%/}/.llama_write_probe.$$"
if ! : > "${write_probe}" 2>/dev/null; then
  print_model_diagnostics
  die "Model directory is not writable: ${LLM_MODEL_PATH}"
fi
rm -f "${write_probe}"

log "Waiting for model: ${MODEL_FULL_PATH}"
deadline=$(( $(date +%s) + LLAMA_WAIT_SECONDS ))

while [ ! -f "${MODEL_FULL_PATH}" ]; do
  validate_model_path_state
  if [ "$(date +%s)" -ge "$deadline" ]; then
    print_model_diagnostics
    log "Timeout after ${LLAMA_WAIT_SECONDS}s. Exiting."
    exit 1
  fi
  sleep "${LLAMA_POLL_SECONDS}"
done

# Wait until file size is stable
prev=-1; stable=0
while [ $stable -lt 3 ]; do
  validate_model_path_state
  size=$(stat -c%s "${MODEL_FULL_PATH}" 2>/dev/null || echo 0)
  if [ "$size" -gt 0 ] && [ "$size" -eq "$prev" ]; then
    stable=$((stable+1))
  else
    stable=0
    prev="$size"
  fi
  sleep 2
done

# Find llama-server executable
LLAMA_BIN=$(which llama-server 2>/dev/null || echo "")
if [ -z "$LLAMA_BIN" ] && [ -f "/app/llama-server" ]; then
    LLAMA_BIN="/app/llama-server"
fi

if [ -z "$LLAMA_BIN" ]; then
    echo "[llama] Error: llama-server executable not found"
    exit 1
fi

# Ensure /app libraries are available
export LD_LIBRARY_PATH="/app:${LD_LIBRARY_PATH:-}"

echo "[llama] Starting llama-server on ${LLAMA_HOST}:${LLAMA_PORT}"
exec "$LLAMA_BIN" \
  --model "${MODEL_FULL_PATH}" \
  --host "${LLAMA_HOST}" \
  --port "${LLAMA_PORT}" \
  -ngl "${LLAMA_NGL}" \
  --ctx-size "${LLAMA_CTX_SIZE}" \
  --threads "${LLAMA_THREADS}" \
  --parallel "${LLAMA_PARALLEL}" \
  -b 512 \
  ${LLAMA_ARGS:-}
