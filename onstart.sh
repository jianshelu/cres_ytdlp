#!/bin/bash
# Refined onstart.sh for Vast.ai
LOGFILE="/var/log/onstart.log"
echo "[$(date)] Instance starting..." > $LOGFILE

# Ensure we are in workspace
cd /workspace

# Explicitly set PATH
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.deno/bin:/workspace:$PATH
export CONTROL_PLANE_MODE="${CONTROL_PLANE_MODE:-external}"
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-100.121.250.72:7233}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-100.121.250.72:9000}"
export MINIO_SECURE="${MINIO_SECURE:-false}"

# Fix line endings just in case
sed -i 's/\r$//' /workspace/*.sh

# Ensure executability
chmod +x /workspace/*.sh

# Call the refined remote startup script
if [ -f "./start_remote.sh" ]; then
    echo "[$(date)] Calling start_remote.sh..." >> $LOGFILE
    ./start_remote.sh >> $LOGFILE 2>&1
else
    echo "[$(date)] ERROR: start_remote.sh not found!" >> $LOGFILE
fi
