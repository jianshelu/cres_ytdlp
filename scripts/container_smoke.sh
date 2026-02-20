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
API_PORT="${API_PORT:-8100}"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:${API_PORT}/health}"

for i in $(seq 1 60); do
  if curl -fsS "${API_HEALTH_URL}" >/dev/null; then
    break
  fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${API_PORT}/docs" >/dev/null
echo "fastapi docs ok"

echo "[smoke] start workers on-demand..."
SMOKE_REQUIRE_GPU_QUEUE="${SMOKE_REQUIRE_GPU_QUEUE:-auto}"
SMOKE_EXPECT_GPU_QUEUE="0"
if [[ "${SMOKE_REQUIRE_GPU_QUEUE,,}" == "true" || "${SMOKE_REQUIRE_GPU_QUEUE,,}" == "1" || "${SMOKE_REQUIRE_GPU_QUEUE,,}" == "yes" ]]; then
  SMOKE_EXPECT_GPU_QUEUE="1"
elif [[ "${SMOKE_REQUIRE_GPU_QUEUE,,}" == "false" || "${SMOKE_REQUIRE_GPU_QUEUE,,}" == "0" || "${SMOKE_REQUIRE_GPU_QUEUE,,}" == "no" ]]; then
  SMOKE_EXPECT_GPU_QUEUE="0"
else
  SMOKE_EXPECT_GPU_QUEUE="$(python3 - <<'PY'
try:
    import torch  # type: ignore
    print("1" if bool(torch.cuda.is_available()) else "0")
except Exception:
    print("0")
PY
)"
fi
export SMOKE_EXPECT_GPU_QUEUE
echo "[smoke] gpu queue expectation: ${SMOKE_EXPECT_GPU_QUEUE} (SMOKE_REQUIRE_GPU_QUEUE=${SMOKE_REQUIRE_GPU_QUEUE})"

if command -v supervisorctl >/dev/null 2>&1; then
  supervisorctl -s unix:///tmp/supervisor.sock start worker-cpu || true
  if [[ "${SMOKE_EXPECT_GPU_QUEUE}" == "1" ]]; then
    supervisorctl -s unix:///tmp/supervisor.sock start worker-gpu || true
  else
    echo "[smoke] skip worker-gpu start (no GPU expected in this environment)"
  fi
else
  echo "supervisorctl not found; skip explicit worker start"
fi

echo "[smoke] check temporal queue registration..."
python3 - <<'PY'
import asyncio
import os
from temporalio.client import Client
from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.api.taskqueue.v1 import TaskQueue

addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
base = (os.getenv("BASE_TASK_QUEUE", "ledge").strip() or "ledge")
expect_gpu = (os.getenv("SMOKE_EXPECT_GPU_QUEUE", "0").strip() == "1")
queues = [f"{base}@cpu"]
if expect_gpu:
    queues.append(f"{base}@gpu")
print(f"queue check targets={queues} expect_gpu={expect_gpu}")

namespace = os.getenv("TEMPORAL_NAMESPACE", "ledge-repo")
async def has_poller(client, q):
    # GPU queue can be activity-only; validate either poller type is present.
    for queue_type in (
        TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
        TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
    ):
        req = DescribeTaskQueueRequest(
            namespace=namespace,
            task_queue=TaskQueue(name=q),
            task_queue_type=queue_type,
        )
        rsp = await client.workflow_service.describe_task_queue(req)
        if rsp.pollers:
            return True
    return False

async def main():
    last_err = None
    for _ in range(60):
        try:
            client = await Client.connect(addr)
        except Exception as e:
            last_err = e
            await asyncio.sleep(1)
            continue

        ok = True
        for q in queues:
            if not await has_poller(client, q):
                ok = False
                break
        if ok:
            print("queue registration ok")
            return
        await asyncio.sleep(1)
    raise SystemExit(f"queue registration failed for {queues} at {addr}; last_err={last_err}")

asyncio.run(main())
PY

echo "[smoke] all checks passed."
