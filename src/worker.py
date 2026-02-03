import asyncio
import concurrent.futures
from temporalio.client import Client
from temporalio.worker import Worker

# Import our workflow and activities
from workflows import VideoProcessingWorkflow
from activities import download_video, transcribe_video, summarize_content

async def main():
    # Connect to the Temporal server using the Docker networking or localhost
    # Since we are running in the same container/network space as CLI:
    client = await Client.connect("localhost:7233")
    
    print("Worker connecting to Temporal server on localhost:7233...")

    # Run the worker
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        worker = Worker(
            client,
            task_queue="video-processing-queue",
            workflows=[VideoProcessingWorkflow],
            activities=[download_video, transcribe_video, summarize_content],
            activity_executor=executor,
        )

        print("Worker started. Waiting for tasks...")
        await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
