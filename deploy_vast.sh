#!/bin/bash
set -e

# Vast.ai connection details
HOST="ssh1.vast.ai"
PORT="12843"
USER="root"
SSH_KEY="/home/rama/.ssh/id_vast.ai70.69"
TARGET_DIR="/workspace"

# Ensure entrypoint is executable locally (good practice)
chmod +x entrypoint.sh

echo "========================================"
echo "Deploying to $USER@$HOST (Port $PORT)"
echo "Target Directory: $TARGET_DIR"
echo "========================================"

# 1. Sync files
# We exclude heavy/generated directories to speed up transfer
# Using .gitignore for exclusions requires it to be clean, preventing sync of ignored files
echo "[1/3] Syncing files..."
rsync -avz -e "ssh -p $PORT -i $SSH_KEY -o StrictHostKeyChecking=no" \
    --exclude-from='.gitignore' \
    --exclude='.git' \
    --exclude='.env' \
    --progress \
    ./ \
    $USER@$HOST:$TARGET_DIR

# 2. Remote Execution
echo "[2/3] Setting up environment and starting services..."
ssh -p $PORT -i $SSH_KEY -o StrictHostKeyChecking=no $USER@$HOST << EOF
    set -e
    cd $TARGET_DIR
    
    echo "Updating system and fixing potential package issues..."
    # Attempt to fix broken installs first
    apt-get update
    apt-get install -y -f
    
    echo "Installing dependencies individually..."
    # Install curl/wget/ffmpeg first
    apt-get install -y ffmpeg curl wget python3-pip || true
    
    # Node.js usually comes from nodesource on these images, try to install it separately
    if ! command -v node &> /dev/null; then
        apt-get install -y nodejs || true
    fi

    echo "Installing Python dependencies..."
    pip3 install --upgrade pip
    pip3 install -r requirements.txt

    echo "Installing Node dependencies..."
    cd web && npm install && npm run build
    cd ..

    echo "Installing Temporal CLI..."
    if ! command -v temporal &> /dev/null; then
        curl -sSf https://temporal.download/cli.sh | sh
        mv /root/.temporalio/bin/temporal /usr/local/bin/
    fi

    echo "Installing MinIO..."
    if [ ! -f /usr/local/bin/minio ]; then
        wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio
        chmod +x /usr/local/bin/minio
        curl -sL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
        chmod +x /usr/local/bin/mc
    fi

    # Killing existing services if any
    echo "Cleaning up existing processes..."
    pkill -9 -f "uvicorn|temporal|minio|node|next|python3 -m src.backend.worker|llama-server" || true
    # Try to free ports if fuser is available
    if command -v fuser &> /dev/null; then
        fuser -k 3000/tcp 8000/tcp 8233/tcp 9000/tcp 9001/tcp || true
    fi
    sleep 2

    echo "Starting services via entrypoint..."
    chmod +x entrypoint.sh
    # We run it with 'nohup' or in background to keep it alive
    # Set required environment variables for the app
    export LLM_MODEL_PATH="/workspace/packages/models/llm"
    export WHISPER_MODEL_PATH="/workspace/packages/models/whisper"
    export XDG_CACHE_HOME="/workspace/.cache"
    export PATH="/workspace:${PATH}"
    
    mkdir -p $LLM_MODEL_PATH $WHISPER_MODEL_PATH /workspace/.cache

    rm -f package.json package-lock.json
    nohup bash -c "cd web && ../entrypoint.sh npm start" > /var/log/app_output.log 2>&1 &

    echo "Services are starting in the background."
    echo "Wait ~30 seconds for everything to initialize."
EOF

echo "[3/3] Deployment script finished."
echo "You can check logs with: ssh -p $PORT -i $SSH_KEY -o StrictHostKeyChecking=no $USER@$HOST 'tail -f /var/log/app_output.log'"
