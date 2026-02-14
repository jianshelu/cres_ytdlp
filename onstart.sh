#!/bin/bash
# Refined onstart.sh for Vast.ai
LOGFILE="/var/log/onstart.log"
echo "[$(date)] Instance starting..." > $LOGFILE

# Ensure we are in workspace
cd /workspace

# Explicitly set PATH
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.deno/bin:/workspace:$PATH
export CONTROL_PLANE_MODE="${CONTROL_PLANE_MODE:-external}"
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-64.229.113.233:7233}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-64.229.113.233:9000}"
export MINIO_SECURE="${MINIO_SECURE:-false}"

# Normalize credential aliases from template env.
# Vast args sometimes use AWS_SECRET_KEY_ID by mistake; map it for compatibility.
if [ -n "${AWS_SECRET_KEY_ID:-}" ] && [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_KEY_ID}"
fi
if [ -z "${MINIO_ACCESS_KEY:-}" ] && [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
    export MINIO_ACCESS_KEY="${AWS_ACCESS_KEY_ID}"
fi
if [ -z "${MINIO_SECRET_KEY:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    export MINIO_SECRET_KEY="${AWS_SECRET_ACCESS_KEY}"
fi
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${MINIO_ACCESS_KEY:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${MINIO_SECRET_KEY:-}}"

# Fail fast if MinIO credentials are missing to avoid silent retry loops.
if [ -z "${MINIO_ACCESS_KEY:-}" ] || [ -z "${MINIO_SECRET_KEY:-}" ]; then
    echo "[$(date)] ERROR: MINIO_ACCESS_KEY/MINIO_SECRET_KEY missing. Worker start aborted." >> "$LOGFILE"
    exit 1
fi

# Fix line endings just in case
sed -i 's/\r$//' /workspace/*.sh

# Ensure executability
chmod +x /workspace/*.sh

# Call the refined remote startup script
if [ -f "./start_remote.sh" ]; then
    echo "[$(date)] Calling start_remote.sh..." >> $LOGFILE
    bash ./start_remote.sh >> $LOGFILE 2>&1
else
    echo "[$(date)] ERROR: start_remote.sh not found!" >> $LOGFILE
fi
