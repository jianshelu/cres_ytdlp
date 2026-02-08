#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    set -a
    [ -f .env ] && . .env
    set +a
fi

# Vast.ai connection details (Defaults or from .env)
HOST="${VAST_HOST:-ssh3.vast.ai}"
PORT="${VAST_PORT:-36535}"
USER="${VAST_USER:-root}"
SSH_KEY="${VAST_SSH_KEY}" # Optional, if empty will use default ssh agent/key
TARGET_DIR="/workspace"

# Determine SSH command (Configured to prefer Linux ssh in WSL for path compatibility)
if [ -f "/usr/bin/ssh" ]; then
    SSH_CMD="/usr/bin/ssh"
else
    SSH_CMD="ssh"
fi

# Construct SSH options
SSH_OPTS="-p $PORT -o StrictHostKeyChecking=no"
# Handle WSL /mnt/c permission issues (keys are 777 usually)
if [[ "$SSH_KEY" == /mnt/c/* ]]; then
    echo "Detected key on Windows partition. Copying to secure temp location to fix permissions..."
    SECURE_KEY="$HOME/.ssh/vast_deploy_key_tmp"
    mkdir -p "$HOME/.ssh"
    cp "$SSH_KEY" "$SECURE_KEY"
    chmod 600 "$SECURE_KEY"
    SSH_KEY="$SECURE_KEY"
fi

if [ -n "$SSH_KEY" ]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
fi

# Ensure entrypoint is executable locally (good practice)
chmod +x entrypoint.sh

echo "========================================"
echo "Deploying to $USER@$HOST (Port $PORT)"
echo "Target Directory: $TARGET_DIR"
echo "Using SSH Key: $SSH_KEY"
echo "========================================"

# 1. Sync files
# We exclude heavy/generated directories to speed up transfer
# Using .gitignore for exclusions requires it to be clean, preventing sync of ignored files
echo "[1/4] Syncing files (via tar+ssh)..."
# Use tar to stream files to remote host (avoids rsync banner issues)
tar -c --exclude='.git' --exclude='.env' --exclude='node_modules' --exclude='.next' --exclude='__pycache__' . | \
    $SSH_CMD $SSH_OPTS $USER@$HOST "mkdir -p $TARGET_DIR && cd $TARGET_DIR && tar -x"

# 2. Check for critical remote dependencies
echo "[2/4] Checking remote dependencies..."
$SSH_CMD $SSH_OPTS $USER@$HOST << EOF
    if ! command -v llama-server &> /dev/null && [ ! -f /usr/bin/llama-server ]; then
        echo "WARNING: llama-server not found in path."
        echo "If you are using the recommend image (ghcr.io/ggml-org/llama.cpp:server-cuda), it should be there."
        echo "Proceeding, but LLM features may fail."
    else
        echo "llama-server found."
    fi
EOF

# 3. Remote Execution
echo "[3/4] Setting up environment and starting services..."
$SSH_CMD $SSH_OPTS $USER@$HOST << EOF
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

echo "[4/4] Deployment script finished."
echo "You can check logs with: ssh $SSH_OPTS $USER@$HOST 'tail -f /var/log/app_output.log'"
echo "To tunnel ports locally: ssh $SSH_OPTS -L 3000:localhost:3000 -L 8000:localhost:8000 -L 8081:localhost:8081 -L 9001:localhost:9001 $USER@$HOST"
