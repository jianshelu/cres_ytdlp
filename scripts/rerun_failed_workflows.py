import asyncio
import json
import os
import time
from dataclasses import dataclass

from temporalio.client import Client

from src.backend.workflows import BatchProcessingWorkflow, CPU_TASK_QUEUE


MAX_FAILED_TO_PROCESS = int(os.getenv("RERUN_MAX_FAILED", "30"))
MAX_ATTEMPTS_PER_WORKFLOW = int(os.getenv("RERUN_MAX_ATTEMPTS", "3"))
WAIT_TIMEOUT_SECONDS = int(os.getenv("RERUN_WAIT_TIMEOUT_SECONDS", "1800"))
REPORT_PATH = os.getenv("RERUN_REPORT_PATH", "/workspace/logs/failed_workflow_rerun_report.json")


@dataclass
class FailedWorkflow:
    workflow_id: str
    run_id: str
    status: str


def parse_query_from_id(workflow_id: str) -> str:
    if not workflow_id.startswith("batch-"):
        return workflow_id
    core = workflow_id[len("batch-") :]
    parts = core.split("-")
    if len(parts) <= 1:
        return core
    return "-".join(parts[:-1])


async def list_failed_batches(client: Client) -> list[FailedWorkflow]:
    rows: list[FailedWorkflow] = []
    async for wf in client.list_workflows():
        if not wf.id.startswith("batch-") or str(wf.workflow_type) != "BatchProcessingWorkflow":
            continue
        if str(wf.status) not in {"WorkflowExecutionStatus.FAILED", "FAILED"}:
            continue
        rows.append(
            FailedWorkflow(
                workflow_id=wf.id,
                run_id=wf.run_id,
                status=str(wf.status),
            )
        )
        if len(rows) >= MAX_FAILED_TO_PROCESS:
            break
    return rows


async def wait_result(handle, timeout_s: int):
    try:
        await asyncio.wait_for(handle.result(), timeout=timeout_s)
        return True, None
    except Exception as exc:  # pragma: no cover - runtime integration path
        return False, f"{type(exc).__name__}: {exc}"


async def rerun_one(client: Client, failed: FailedWorkflow):
    # Note: We can reliably infer query slug from current workflow-id naming.
    # For old/history workflows with custom ids this may be imperfect.
    query = parse_query_from_id(failed.workflow_id)
    args = (query, 5, 2, 10)

    attempts: list[dict] = []
    for attempt in range(1, MAX_ATTEMPTS_PER_WORKFLOW + 1):
        new_id = f"{failed.workflow_id}-rerun-{int(time.time())}-{attempt}"
        try:
            handle = await client.start_workflow(
                BatchProcessingWorkflow.run,
                args,
                id=new_id,
                task_queue=CPU_TASK_QUEUE,
            )
        except Exception as exc:  # pragma: no cover - runtime integration path
            attempts.append(
                {
                    "attempt": attempt,
                    "workflow_id": new_id,
                    "started": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        ok, err = await wait_result(handle, WAIT_TIMEOUT_SECONDS)
        if ok:
            attempts.append(
                {
                    "attempt": attempt,
                    "workflow_id": new_id,
                    "started": True,
                    "status": "completed",
                }
            )
            return True, attempts

        attempts.append(
            {
                "attempt": attempt,
                "workflow_id": new_id,
                "started": True,
                "status": "failed",
                "error": err,
            }
        )
    return False, attempts


async def main():
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(temporal_address)
    failed = await list_failed_batches(client)
    print(f"Found failed batch workflows: {len(failed)}")

    report: dict = {
        "temporal_address": temporal_address,
        "total_failed_seen": len(failed),
        "completed": 0,
        "still_failed": 0,
        "processed": [],
    }

    for idx, wf in enumerate(failed, 1):
        print(f"[{idx}/{len(failed)}] rerun {wf.workflow_id}")
        ok, attempts = await rerun_one(client, wf)
        report["processed"].append(
            {
                "original": {
                    "workflow_id": wf.workflow_id,
                    "run_id": wf.run_id,
                    "status": wf.status,
                },
                "ok": ok,
                "attempts": attempts,
            }
        )
        if ok:
            report["completed"] += 1
        else:
            report["still_failed"] += 1

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    summary = {
        "total_failed_seen": report["total_failed_seen"],
        "completed": report["completed"],
        "still_failed": report["still_failed"],
    }
    print("---SUMMARY---")
    print(json.dumps(summary, ensure_ascii=False))
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
