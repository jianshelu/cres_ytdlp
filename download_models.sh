#!/bin/bash
set -e

LLM_DIR="/workspace/packages/models/llm"
WHISPER_DIR="/workspace/packages/models/whisper"

mkdir -p "$LLM_DIR" "$WHISPER_DIR"

echo "Downloading Gemma 3 1b IT Q4_K_M to $LLM_DIR/tmp_model.gguf..."
if [ ! -f "$LLM_DIR/google_gemma-3-1b-it-Q4_K_M.gguf" ]; then
    ls -la "$LLM_DIR"
    curl -L "https://huggingface.co/bartowski/google_gemma-3-1b-it-GGUF/resolve/main/google_gemma-3-1b-it-Q4_K_M.gguf" -o "$LLM_DIR/tmp_model.gguf"
    mv "$LLM_DIR/tmp_model.gguf" "$LLM_DIR/google_gemma-3-1b-it-Q4_K_M.gguf"
fi

echo "Models download complete."
