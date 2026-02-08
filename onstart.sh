#!/bin/bash
# This file is run on instance start by Vast.ai.
# Set the "On-start script" field in the Vast.ai console to: bash /workspace/onstart.sh

LOGFILE="/var/log/onstart_trace.log"
echo "[$(date)] Instance starting..." >> $LOGFILE

# Ensure we are in workspace
cd /workspace

# Explicitly set PATH for background services
export PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin:/workspace:$PATH

# Call the refined remote startup script
if [ -f "./start_remote.sh" ]; then
    echo "[$(date)] Calling start_remote.sh..." >> $LOGFILE
    bash ./start_remote.sh >> $LOGFILE 2>&1
else
    echo "[$(date)] ERROR: start_remote.sh not found!" >> $LOGFILE
fi
