#!/bin/bash
cd /workspace
# Kill existing
echo "Killing old processes..."
for port in 3000 8000 9000 9001 7233 8233 8081; do
    fuser -k -n tcp $port 2>/dev/null || true
done
pkill -9 -f "minio|temporal|uvicorn|python3|node|next" || true
sleep 3


echo "Starting services via entrypoint..."
export LLM_MODEL_PATH="/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
nohup ./entrypoint.sh bash -c "cd web && npm start" > /workspace/logs/app.log 2>&1 &
echo "Started."
