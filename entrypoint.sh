#!/bin/bash
set -e

echo "Starting services..."

# Start MinIO in the background
mkdir -p /data/minio
echo "Starting MinIO..."
minio server /data/minio --address ":9000" --console-address ":9001" > /var/log/minio.log 2>&1 &

# Wait for MinIO to be ready
echo "Waiting for MinIO to start..."
MAX_RETRIES=30
COUNT=0
until curl -s http://localhost:9000/minio/health/live || [ $COUNT -eq $MAX_RETRIES ]; do
  sleep 1
  COUNT=$((COUNT + 1))
done

if [ $COUNT -eq $MAX_RETRIES ]; then
  echo "MinIO failed to start"
  exit 1
fi

echo "MinIO is ready."

# Configure mc
echo "Configuring MinIO client..."
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/videos --ignore-existing

# Start Temporal Dev Server if requested or as default
# Note: In a production environment on vast.ai, you might want a persistent Temporal cluster,
# but for standalone Docker, start-dev is useful.
echo "Starting Temporal dev server..."
temporal server start-dev --ip 0.0.0.0 > /var/log/temporal.log 2>&1 &

# Wait for Temporal
echo "Waiting for Temporal..."
COUNT=0
until temporal operator cluster health || [ $COUNT -eq $MAX_RETRIES ]; do
  sleep 1
  COUNT=$((COUNT + 1))
done

# Start LLM Server if model is present
if [ -d "$LLM_MODEL_PATH" ] && [ "$(ls $LLM_MODEL_PATH/*.gguf 2>/dev/null)" ]; then
    echo "Starting LLM server..."
    # Find the first .gguf file
    MODEL_FILE=$(find $LLM_MODEL_PATH -name "*.gguf" | head -n 1)
    if [ -n "$MODEL_FILE" ]; then
        LLAMA_BIN=$(which llama-server || echo "/usr/bin/llama-server")
        if [ ! -f "$LLAMA_BIN" ] && [ -f "/app/llama-server" ]; then
            LLAMA_BIN="/app/llama-server"
        fi
        
        export LD_LIBRARY_PATH="/app:${LD_LIBRARY_PATH}"
        $LLAMA_BIN --model "$MODEL_FILE" --host 0.0.0.0 --port 8081 --n-gpu-layers 99 > /var/log/llama.log 2>&1 &
        echo "LLM server starting with model: $MODEL_FILE"
    else
        echo "No .gguf model found in $LLM_MODEL_PATH, skipping LLM server start."
    fi
else
    echo "LLM_MODEL_PATH is empty or missing, skipping LLM server start."
fi

# Start FastAPI
echo "Starting FastAPI..."
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /var/log/fastapi.log 2>&1 &

# Start Temporal Worker (Background)
echo "Starting Temporal Worker..."
# Wait a bit for Temporal Server to be fully ready (though we waited for cluster health above)
python3 -m src.backend.worker > /var/log/worker.log 2>&1 &

echo "Services started successfully."

# Execute the main command
exec "$@"
