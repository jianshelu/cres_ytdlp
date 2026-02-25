"""CPU Worker - Temporal worker for CPU tasks (@cpu queue)."""

import asyncio
import os

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from src.shared import settings, TASK_QUEUE_CPU, get_logger

logger = get_logger("worker_cpu")


@activity.defn
async def metadata_process(data: dict) -> dict:
    """Process metadata (CPU-bound task)."""
    return {"processed": True, "data": data}


@activity.defn
async def result_format(data: dict) -> dict:
    """Format results (CPU-bound task)."""
    return {"formatted": True, "data": data}


async def main():
    endpoint = os.getenv("TEMPORAL_ADDRESS", settings.temporal.endpoint)
    logger.info(f"Connecting to Temporal at {endpoint}")
    
    client = await Client.connect(
        endpoint,
        namespace=settings.temporal.namespace,
    )
    
    logger.info(f"Starting CPU worker on queue: {TASK_QUEUE_CPU}")
    
    async with Worker(
        client,
        task_queue=TASK_QUEUE_CPU,
        workflows=[],
        activities=[metadata_process, result_format],
        max_concurrent_activities=4,
    ):
        logger.info("CPU worker started successfully")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
