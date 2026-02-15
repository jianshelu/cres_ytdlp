#!/bin/bash
set -euo pipefail

LLM_DIR="/workspace/packages/models/llm"
WHISPER_DIR="/workspace/packages/models/whisper"

mkdir -p "$LLM_DIR" "$WHISPER_DIR"

MODEL_FILE="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
MODEL_URL="https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/${MODEL_FILE}"
MODEL_PATH="${LLM_DIR}/${MODEL_FILE}"
TMP_PATH="${MODEL_PATH}.part"

echo "Downloading ${MODEL_FILE} to ${MODEL_PATH} (resume supported)..."
if [ ! -f "$MODEL_PATH" ]; then
  ls -la "$LLM_DIR" || true
  curl -fL --retry 5 --retry-delay 2 --connect-timeout 15 -C - -o "$TMP_PATH" "$MODEL_URL"
  size="$(stat -c%s "$TMP_PATH" 2>/dev/null || echo 0)"
  if [ "${size}" -le 0 ]; then
    rm -f "$TMP_PATH" || true
    echo "ERROR: download produced empty file: ${TMP_PATH}" 1>&2
    exit 1
  fi
  mv -f "$TMP_PATH" "$MODEL_PATH"
  echo "Downloaded: ${MODEL_PATH} (${size} bytes)"
else
  echo "OK: already present: ${MODEL_PATH}"
fi

echo "Models download complete."
