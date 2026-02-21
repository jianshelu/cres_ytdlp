#!/usr/bin/env bash
set -euo pipefail

# Start llama.cpp server
# Must match $triage constraints: -ngl 999, -b 512, --threads 8

if [ "${LLAMA_DISABLE:-0}" = "1" ]; then
  echo "[llama] LLAMA_DISABLE=1, skipping llama start"
  exit 0
fi

# Defaults: model sync happens after deploy
LLM_MODEL_DIR="${LLM_MODEL_PATH:-/workspace/packages/models/llm}"
LLM_MODEL_FILE="${LLM_MODEL_FILE:-Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
MODEL_PATH="${MODEL_PATH:-${LLM_MODEL_DIR}/${LLM_MODEL_FILE}}"

resolve_llama_server() {
  local candidate
  for candidate in \
    "${LLAMA_SERVER:-}" \
    "/usr/local/bin/llama-server" \
    "/app/llama-server" \
    "/workspace/packages/llama.cpp/server"
  do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

LLAMA_SERVER_BIN="$(resolve_llama_server || true)"
if [ -z "$LLAMA_SERVER_BIN" ]; then
  echo "[llama] llama-server binary not found; tried /usr/local/bin/llama-server, /app/llama-server, /workspace/packages/llama.cpp/server"
  echo "[llama] skipping llama start"
  exit 0
fi

if [ ! -f "$MODEL_PATH" ]; then
    MODEL_PATH="$(ls -1 "${LLM_MODEL_DIR}"/*.gguf 2>/dev/null | head -n 1 || true)"
fi

if [ -z "$MODEL_PATH" ] || [ ! -f "$MODEL_PATH" ]; then
    echo "[llama] LLM model not found under ${LLM_MODEL_DIR}; skip start (model may be synced later)"
    exit 0
fi

echo "[llama] Starting llama.cpp server with model: ${MODEL_PATH}"
echo "[llama] Using binary: ${LLAMA_SERVER_BIN}"

exec "$LLAMA_SERVER_BIN" \
    --model "$MODEL_PATH" \
    --host 0.0.0.0 \
    --port 8081 \
    --ngl 999 \
    --ctx-size 4096 \
    --batch-size 512 \
    --threads 8 \
    --log-disable
