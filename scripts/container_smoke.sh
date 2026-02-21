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
    "pypinyin",
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
API_HEALTH_URL=""
for p in 8100 8000; do
  for i in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${p}/health" >/dev/null; then
      API_HEALTH_URL="http://127.0.0.1:${p}/health"
      API_DOCS_URL="http://127.0.0.1:${p}/docs"
      break 2
    fi
    sleep 1
  done
done
if [ -z "${API_HEALTH_URL}" ]; then
  echo "[smoke] FastAPI not reachable on 8100/8000"
  command -v supervisorctl >/dev/null 2>&1 && supervisorctl -c /etc/supervisor/supervisord.conf status || true
  ss -lntp || netstat -lntp || true
  exit 7
fi
curl -fsS "${API_DOCS_URL}" >/dev/null
echo "fastapi docs ok (${API_DOCS_URL})"

if [ "${SMOKE_SKIP_WORKER_CHECKS:-0}" = "1" ]; then
  echo "[smoke] SMOKE_SKIP_WORKER_CHECKS=1, skip worker and Temporal queue checks"
  echo "[smoke] all checks passed."
  exit 0
fi

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
  supervisorctl -c /etc/supervisor/supervisord.conf start worker-cpu || true
  if [ "${WORKER_GPU_OPTIONAL:-0}" = "1" ] && [ "${SMOKE_EXPECT_GPU_QUEUE}" = "0" ]; then
    echo "[smoke] stop optional worker-gpu (no GPU expected)"
    supervisorctl -c /etc/supervisor/supervisord.conf stop worker-gpu || true
  fi
  if [[ "${SMOKE_EXPECT_GPU_QUEUE}" == "1" ]]; then
    supervisorctl -c /etc/supervisor/supervisord.conf start worker-gpu || true
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
from temporalio.service import RPCError, RPCStatusCode
from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.workflowservice.v1 import (
    DescribeNamespaceRequest,
    DescribeTaskQueueRequest,
    RegisterNamespaceRequest,
)
from temporalio.api.taskqueue.v1 import TaskQueue
from google.protobuf.duration_pb2 import Duration
addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
expect_gpu = (os.getenv("SMOKE_EXPECT_GPU_QUEUE", "0").strip() == "1")
task_queue_cpu = os.getenv("TASK_QUEUE_CPU", "").strip()
task_queue_gpu = os.getenv("TASK_QUEUE_GPU", "").strip()
if not task_queue_cpu or not task_queue_gpu:
    try:
        from src.shared.constants import TASK_QUEUE_CPU as DEFAULT_CPU_QUEUE
        from src.shared.constants import TASK_QUEUE_GPU as DEFAULT_GPU_QUEUE
        task_queue_cpu = task_queue_cpu or DEFAULT_CPU_QUEUE
        task_queue_gpu = task_queue_gpu or DEFAULT_GPU_QUEUE
    except Exception:
        base = (os.getenv("BASE_TASK_QUEUE", "ledge").strip() or "ledge")
        task_queue_cpu = task_queue_cpu or f"{base}@cpu"
        task_queue_gpu = task_queue_gpu or f"{base}@gpu"
queues = [task_queue_cpu]
if expect_gpu:
    queues.append(task_queue_gpu)
print(f"queue check targets={queues} expect_gpu={expect_gpu}")

namespace = os.getenv("TEMPORAL_NAMESPACE", "ledge-repo")
async def ensure_namespace(client, ns):
    try:
        await client.workflow_service.describe_namespace(
            DescribeNamespaceRequest(namespace=ns)
        )
        return
    except RPCError as e:
        if e.status != RPCStatusCode.NOT_FOUND:
            raise
    try:
        await client.workflow_service.register_namespace(
            RegisterNamespaceRequest(
                namespace=ns,
                workflow_execution_retention_period=Duration(seconds=86400),
            )
        )
        print(f"namespace created: {ns}")
    except RPCError as e:
        if e.status != RPCStatusCode.ALREADY_EXISTS:
            raise
    # Namespace creation on start-dev can be eventually consistent.
    for _ in range(30):
        try:
            await client.workflow_service.describe_namespace(
                DescribeNamespaceRequest(namespace=ns)
            )
            return
        except RPCError as e:
            if e.status != RPCStatusCode.NOT_FOUND:
                raise
            await asyncio.sleep(1)
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
        try:
            rsp = await client.workflow_service.describe_task_queue(req)
        except RPCError as e:
            # Namespace can still be propagating right after registration.
            if e.status == RPCStatusCode.NOT_FOUND:
                return False
            raise
        if rsp.pollers:
            return True
    return False

async def main():
    last_err = None
    for _ in range(60):
        try:
            client = await Client.connect(addr)
            await ensure_namespace(client, namespace)
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
