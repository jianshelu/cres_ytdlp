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
]
if (importlib.import_module("os").getenv("SMOKE_VALIDATE_GPU_STACK", "0") == "1"):
    mods += ["faster_whisper", "torch"]
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
check_fastapi_docs() {
  python3 - <<'PY'
import sys
import urllib.request

url = "http://127.0.0.1:8000/docs"
try:
    with urllib.request.urlopen(url, timeout=2) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
}

if ! check_fastapi_docs >/dev/null 2>&1; then
  echo "[smoke] FastAPI not running, starting uvicorn..."
  python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 >/tmp/smoke-api.log 2>&1 &
  SMOKE_API_PID=$!
else
  SMOKE_API_PID=""
fi

for i in $(seq 1 60); do
  if check_fastapi_docs >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
check_fastapi_docs >/dev/null
echo "fastapi docs ok"

echo "[smoke] start worker process (both queues)..."
WORKER_MODE=both WORKER_CPU_THREADS=1 WORKER_GPU_THREADS=1 python3 -m src.backend.worker >/tmp/smoke-worker.log 2>&1 &
SMOKE_WORKER_PID=$!
cleanup() {
  if [ -n "${SMOKE_API_PID:-}" ] && kill -0 "$SMOKE_API_PID" >/dev/null 2>&1; then
    kill "$SMOKE_API_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${SMOKE_WORKER_PID:-}" ] && kill -0 "$SMOKE_WORKER_PID" >/dev/null 2>&1; then
    kill "$SMOKE_WORKER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
sleep 2
if ! kill -0 "$SMOKE_WORKER_PID" >/dev/null 2>&1; then
  echo "worker failed to start"
  cat /tmp/smoke-worker.log || true
  exit 1
fi

echo "[smoke] check temporal queue registration..."
if ! python3 - <<'PY'
import asyncio
import os
from temporalio.client import Client
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.enums.v1.task_queue_pb2 import TASK_QUEUE_TYPE_ACTIVITY

addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
queues = ["video-processing-queue", "video-gpu-queue"]

async def has_poller(client, q):
    req = DescribeTaskQueueRequest(
        namespace="default",
        task_queue=TaskQueue(name=q),
        task_queue_type=TASK_QUEUE_TYPE_ACTIVITY,
    )
    rsp = await client.workflow_service.describe_task_queue(req)
    return bool(rsp.pollers)

async def main():
    # Temporal may take a bit to become reachable on fresh CI networks.
    client = None
    last_err = None
    for _ in range(60):
        try:
            client = await Client.connect(addr)
            break
        except Exception as e:
            last_err = e
            await asyncio.sleep(1)
    if client is None:
        raise SystemExit(f"temporal connect failed at {addr}: {last_err}")

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
then
  echo "[smoke] queue check failed; worker log:"
  cat /tmp/smoke-worker.log || true
  exit 1
fi

echo "[smoke] all checks passed."
