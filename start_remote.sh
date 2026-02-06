#!/bin/bash
# Unified Service Startup Script
cd /workspace

# 1. Process Cleanup (Killing existing services to avoid port conflicts)
echo "Cleaning up existing processes..."
pkill -9 -f "minio|temporal|uvicorn|python3|node|next|llama-server" || true
if command -v fuser &> /dev/null; then
    fuser -k 3000/tcp 8000/tcp 8233/tcp 9000/tcp 9001/tcp 8081/tcp 2>/dev/null || true
fi
sleep 2

# 2. Environment Setup
export LLM_MODEL_PATH="${LLM_MODEL_PATH:-/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
export WHISPER_MODEL_PATH="${WHISPER_MODEL_PATH:-/workspace/packages/models/whisper}"
export PATH="/usr/local/bin:/usr/bin:/bin:/workspace:${PATH}"

mkdir -p /workspace/logs

# 3. Start Services via entrypoint
# We use nohup and backgrounding to ensure persistence
echo "Starting services via entrypoint..."
nohup ./entrypoint.sh bash -c "cd web && npm start" > /workspace/logs/app.log 2>&1 &

echo "Started. Monitor status with: ps aux | grep -E 'node|uvicorn|temporal|minio'"
