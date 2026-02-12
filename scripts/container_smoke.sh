#!/bin/bash
set -euo pipefail

echo "[smoke] starting container smoke checks..."

echo "[smoke] check python imports..."
python3 - <<'PY'
import importlib
mods = [
    "fastapi",
    "uvicorn",
    "httpx",
    "temporalio",
    "minio",
    "yt_dlp",
    "faster_whisper",
    "torch",
]
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        missing.append(f"{m}: {e}")
if missing:
    raise SystemExit("Missing imports:\n" + "\n".join(missing))
print("imports ok")
PY

echo "[smoke] wait FastAPI..."
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/docs >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/docs >/dev/null
echo "fastapi docs ok"

echo "[smoke] start workers on-demand..."
if command -v supervisorctl >/dev/null 2>&1; then
  supervisorctl -s unix:///tmp/supervisor.sock start worker-cpu || true
  supervisorctl -s unix:///tmp/supervisor.sock start worker-gpu || true
else
  echo "supervisorctl not found; skip explicit worker start"
fi

echo "[smoke] check temporal queue registration..."
python3 - <<'PY'
import asyncio
import os
from temporalio.client import Client
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.api.taskqueue.v1 import TaskQueue

addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
base = (os.getenv("BASE_TASK_QUEUE", "video-processing") or "video-processing").strip()
queues = [f"{base}@cpu", f"{base}@gpu"]

async def has_poller(client, q):
    req = DescribeTaskQueueRequest(
        namespace="default",
        task_queue=TaskQueue(name=q),
    )
    rsp = await client.workflow_service.describe_task_queue(req)
    return bool(rsp.pollers)

async def main():
    client = await Client.connect(addr)
    for _ in range(40):
        ok = True
        for q in queues:
            if not await has_poller(client, q):
                ok = False
                break
        if ok:
            print("queue registration ok")
            return
        await asyncio.sleep(1)
    raise SystemExit(f"queue registration failed for {queues} at {addr}")

asyncio.run(main())
PY

echo "[smoke] all checks passed."
