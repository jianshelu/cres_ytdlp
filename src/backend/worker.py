import asyncio
import concurrent.futures
from temporalio.client import Client
from temporalio.worker import Worker

# Import our workflow and activities
from src.backend.workflows import VideoProcessingWorkflow, BatchProcessingWorkflow
from src.backend.activities import download_video, transcribe_video, summarize_content, search_videos, refresh_index

import torch
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    # Connect to the Temporal server using the Docker networking or localhost
    # Since we are running in the same container/network space as CLI:
    client = await Client.connect("localhost:7233")
    
    print("Worker connecting to Temporal server on localhost:7233...")

    # Determine identity
    import socket
    hostname = socket.gethostname()
    device_type = "gpu" if torch.cuda.is_available() else "cpu"
    identity = f"{hostname}@{device_type}"
    print(f"Worker Identity: {identity}")

    # Run the worker
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        worker = Worker(
            client,
            task_queue="video-processing-queue",
            workflows=[VideoProcessingWorkflow, BatchProcessingWorkflow],
            activities=[download_video, transcribe_video, summarize_content, search_videos, refresh_index],
            activity_executor=executor,
            identity=identity,
        )

        print("Worker started. Waiting for tasks...")
        await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
