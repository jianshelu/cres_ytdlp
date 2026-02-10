import asyncio
import concurrent.futures
import os
from temporalio.client import Client
from temporalio.worker import Worker

# Import our workflow and activities
from src.backend.workflows import (
    VideoProcessingWorkflow,
    BatchProcessingWorkflow,
    ReprocessVideoWorkflow,
    QueryDispatcherWorkflow,
    QueryOrchestratorWorkflow,
)
from src.backend.activities import (
    download_video,
    transcribe_video,
    summarize_content,
    search_videos,
    refresh_index,
    build_batch_combined_output,
)

import torch
import logging

logging.basicConfig(level=logging.INFO)

CPU_TASK_QUEUE = "video-processing-queue"
GPU_TASK_QUEUE = "video-gpu-queue"

async def main():
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(temporal_address)
    print(f"Worker connecting to Temporal server on {temporal_address}...")

    # Determine identity
    import socket
    hostname = socket.gethostname()
    device_type = "gpu" if torch.cuda.is_available() else "cpu"
    print(f"Worker Identity (auto-detected device): {hostname}@{device_type}")
    worker_mode = os.getenv("WORKER_MODE", "both").strip().lower()
    if worker_mode not in {"cpu", "gpu", "both"}:
        worker_mode = "both"
    print(f"Worker Mode: {worker_mode}")

    cpu_workers = max(1, int(os.getenv("WORKER_CPU_THREADS", "4")))
    gpu_workers = max(1, int(os.getenv("WORKER_GPU_THREADS", "2")))

    workers = []
    executors = []

    if worker_mode in {"cpu", "both"}:
        cpu_executor = concurrent.futures.ThreadPoolExecutor(max_workers=cpu_workers)
        executors.append(cpu_executor)
        workers.append(
            Worker(
                client,
                task_queue=CPU_TASK_QUEUE,
                workflows=[
                    VideoProcessingWorkflow,
                    BatchProcessingWorkflow,
                    ReprocessVideoWorkflow,
                    QueryDispatcherWorkflow,
                    QueryOrchestratorWorkflow,
                ],
                activities=[
                    download_video,
                    search_videos,
                    refresh_index,
                    build_batch_combined_output,
                ],
                activity_executor=cpu_executor,
                identity=f"{hostname}@cpu",
            )
        )
        print(f"CPU queue worker attached to '{CPU_TASK_QUEUE}' with threads={cpu_workers}")

    if worker_mode in {"gpu", "both"}:
        gpu_executor = concurrent.futures.ThreadPoolExecutor(max_workers=gpu_workers)
        executors.append(gpu_executor)
        workers.append(
            Worker(
                client,
                task_queue=GPU_TASK_QUEUE,
                workflows=[],
                activities=[
                    transcribe_video,
                    summarize_content,
                ],
                activity_executor=gpu_executor,
                identity=f"{hostname}@gpu",
            )
        )
        print(f"GPU queue worker attached to '{GPU_TASK_QUEUE}' with threads={gpu_workers}")

    if not workers:
        raise RuntimeError("No worker configured. Set WORKER_MODE to cpu, gpu, or both.")

    try:
        print("Worker(s) started. Waiting for tasks...")
        await asyncio.gather(*(w.run() for w in workers))
    finally:
        for ex in executors:
            ex.shutdown(wait=False, cancel_futures=True)

if __name__ == "__main__":
    asyncio.run(main())
