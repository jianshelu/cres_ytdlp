#!/bin/bash
set -e
cd /workspace
mkdir -p /workspace/run
pkill -f "uvicorn src.api.main:app --host 0.0.0.0 --port 8000" || true
pkill -f "python3 -m src.backend.worker" || true
sleep 1
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /var/log/fastapi.log 2>&1 &
echo $! > /workspace/run/cres_fastapi.pid
nohup python3 -m src.backend.worker > /var/log/worker.log 2>&1 &
echo $! > /workspace/run/cres_worker.pid
sleep 3
code=$(curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health || true)
echo "8000:$code"
ps -ef | grep -E "uvicorn src.api.main:app|python3 -m src.backend.worker" | grep -v grep || true