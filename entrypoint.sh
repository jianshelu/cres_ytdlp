#!/bin/bash
set -e
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
if [ ! -w "$WORKSPACE_ROOT" ]; then
    WORKSPACE_ROOT="$(pwd)"
fi
PID_DIR="$WORKSPACE_ROOT/run"
mkdir -p "$PID_DIR"
CONTROL_PLANE_MODE="${CONTROL_PLANE_MODE:-external}"
TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-64.229.113.233:7233}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-64.229.113.233:9000}"
MINIO_SECURE="${MINIO_SECURE:-false}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
REINDEX_URL="${REINDEX_URL:-http://64.229.113.233:8000/admin/reindex}"
export WORKSPACE_ROOT

echo "Starting services..."

# Install Deno if not present (required for yt-dlp to solve YouTube n-challenge)
if [ ! -f /root/.deno/bin/deno ]; then
    echo "Installing Deno for yt-dlp..."
    apt-get install -y unzip > /dev/null 2>&1 || true
    curl -fsSL https://deno.land/install.sh | sh > /dev/null 2>&1
fi
export PATH="/root/.deno/bin:$PATH"

# Install yt-dlp-ejs if not present
python3 -c "import yt_dlp_ejs" 2>/dev/null || pip3 install yt-dlp-ejs > /dev/null 2>&1

if [ "$CONTROL_PLANE_MODE" != "external" ]; then
    echo "CONTROL_PLANE_MODE=$CONTROL_PLANE_MODE is not supported in this image. Forcing external mode."
    CONTROL_PLANE_MODE="external"
fi
echo "Using external control plane endpoints."
echo "TEMPORAL_ADDRESS=$TEMPORAL_ADDRESS"
echo "MINIO_ENDPOINT=$MINIO_ENDPOINT"

export CONTROL_PLANE_MODE TEMPORAL_ADDRESS MINIO_ENDPOINT MINIO_SECURE MINIO_ACCESS_KEY MINIO_SECRET_KEY REINDEX_URL

# Start LLM Server if model is present
# Start LLM Server if model is present
if [ -n "$LLM_MODEL_PATH" ]; then
    MODEL_FILE=""
    if [ -f "$LLM_MODEL_PATH" ]; then
        MODEL_FILE="$LLM_MODEL_PATH"
    elif [ -d "$LLM_MODEL_PATH" ]; then
        MODEL_FILE=$(find "$LLM_MODEL_PATH" -name "*.gguf" | head -n 1)
    fi

    if [ -n "$MODEL_FILE" ] && [ -f "$MODEL_FILE" ]; then
        echo "Starting LLM server..."
        LLAMA_BIN=$(which llama-server || echo "/usr/bin/llama-server")
        if [ ! -f "$LLAMA_BIN" ] && [ -f "/app/llama-server" ]; then
            LLAMA_BIN="/app/llama-server"
        fi
        
        export LD_LIBRARY_PATH="/app:${LD_LIBRARY_PATH}"
        $LLAMA_BIN --model "$MODEL_FILE" --host 0.0.0.0 --port 8081 --n-gpu-layers 99 > /var/log/llama.log 2>&1 &
        echo $! > "$PID_DIR/cres_llama.pid"
        echo "LLM server starting with model: $MODEL_FILE"
    else
        echo "No .gguf model found at $LLM_MODEL_PATH, skipping LLM server start."
    fi
else
    echo "LLM_MODEL_PATH is empty, skipping LLM server start."
fi

# Start FastAPI
echo "Starting FastAPI..."
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /var/log/fastapi.log 2>&1 &
echo $! > "$PID_DIR/cres_fastapi.pid"

# Start Temporal Worker (Background)
echo "Starting Temporal Worker..."
# Wait a bit for Temporal Server to be fully ready (though we waited for cluster health above)
python3 -m src.backend.worker > /var/log/worker.log 2>&1 &
echo $! > "$PID_DIR/cres_worker.pid"

echo "Services started successfully."

# Execute the main command
exec "$@"
