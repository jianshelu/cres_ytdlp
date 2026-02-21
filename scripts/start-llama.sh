#!/bin/bash
# Start llama.cpp server
# Must match $triage constraints: -ngl 999, -b 512, --threads 8

if [ "${LLAMA_DISABLE:-0}" = "1" ]; then
  echo "[llama] LLAMA_DISABLE=1, skipping llama start"
  exit 0
fi

# Defaults: model sync happens after deploy
LLM_MODEL_PATH="${LLM_MODEL_PATH:-/workspace/packages/models/llm}"
LLM_MODEL_FILE="${LLM_MODEL_FILE:-Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
LLM_MODEL_URL="${LLM_MODEL_URL:-https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"

LLM_MODEL_DIR="/workspace/packages/models/llm"
MODEL_PATH="${MODEL_PATH:-${LLM_MODEL_DIR}/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
LLAMA_SERVER="/workspace/packages/llama.cpp/server"

if [ "${LLAMA_DISABLE:-0}" = "1" ]; then
    echo "[llama] LLAMA_DISABLE=1, skipping llama start"
    exit 0
fi

if [ ! -x "$LLAMA_SERVER" ]; then
    echo "[llama] llama.cpp server not found at $LLAMA_SERVER, skipping llama start"
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

exec "$LLAMA_SERVER" \
    --model "$MODEL_PATH" \
    --host 0.0.0.0 \
    --port 8081 \
    --ngl 999 \
    --ctx-size 4096 \
    --batch-size 512 \
    --threads 8 \
    --log-disable
