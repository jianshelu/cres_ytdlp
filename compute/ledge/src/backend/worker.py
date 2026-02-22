"""GPU Worker - Temporal worker for GPU tasks (@gpu queue)."""

import asyncio
import concurrent.futures
import os
import random
import socket
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from src.shared import settings, TASK_QUEUE_GPU, get_logger
from src.backend.activities import stt_transcribe, tts_synthesize
from src.backend.activities.llm_activity import llm_generate
from src.backend.workflows import VoiceConversationWorkflow, TranscribeWorkflow

logger = get_logger("worker_gpu")


def _build_worker_identity() -> str:
    random_id = f"{random.randint(0, 99999):05d}"
    instance_name = settings.instance.host or socket.gethostname()
    return f"gpu{random_id}@{instance_name}"


async def main():
    endpoint = os.getenv("TEMPORAL_ADDRESS", settings.temporal.public_endpoint)
    worker_identity = _build_worker_identity()
    workflow_task_concurrency = int(os.getenv("LEDGE_WORKER_WORKFLOW_TASK_CONCURRENCY", "4"))
    workflow_task_polls = int(os.getenv("LEDGE_WORKER_WORKFLOW_TASK_POLLS", "4"))
    activity_task_polls = int(os.getenv("LEDGE_WORKER_ACTIVITY_TASK_POLLS", "4"))
    logger.info(f"Connecting to Temporal at {endpoint}")
    logger.info(f"Using worker identity: {worker_identity}")
    
    client = await Client.connect(
        endpoint,
        namespace=settings.temporal.namespace,
        identity=worker_identity,
    )
    
    logger.info(f"Starting GPU worker on queue: {TASK_QUEUE_GPU}")

    activity_threads = max(1, int(os.getenv("LEDGE_WORKER_GPU_ACTIVITY_THREADS", "2")))
    activity_executor = concurrent.futures.ThreadPoolExecutor(max_workers=activity_threads)
    
    try:
        async with Worker(
            client,
            task_queue=TASK_QUEUE_GPU,
            workflows=[VoiceConversationWorkflow, TranscribeWorkflow],
            activities=[stt_transcribe, tts_synthesize, llm_generate],
            identity=worker_identity,
            activity_executor=activity_executor,
            max_concurrent_activities=2,
            max_concurrent_workflow_tasks=workflow_task_concurrency,
            max_concurrent_workflow_task_polls=workflow_task_polls,
            max_concurrent_activity_task_polls=activity_task_polls,
            sticky_queue_schedule_to_start_timeout=timedelta(seconds=3),
        ):
            logger.info("GPU worker started successfully")
            await asyncio.Event().wait()
    finally:
        activity_executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    asyncio.run(main())
