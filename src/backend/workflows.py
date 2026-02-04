from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities definition (only for type hinting in sandbox, 
# typically we use string names or stub proxies)
with workflow.unsafe.imports_passed_through():
    from src.backend.activities import download_video, transcribe_video, summarize_content, search_videos, refresh_index

@workflow.defn
class VideoProcessingWorkflow:
    @workflow.run
    async def run(self, url: str) -> dict:
        workflow.logger.info(f"Video processing workflow started for {url}")

        # 1. Download Activity
        # Retry logic: Retrying downloads is generally safe.
        filepath = await workflow.execute_activity(
            download_video,
            url,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )

        # 2. Transcribe Activity
        # This can be long running (GPU based)
        transcript_text = await workflow.execute_activity(
            transcribe_video,
            filepath,
            start_to_close_timeout=timedelta(minutes=60)
        )

        # 3. Summarize Activity
        # OpenAI/Llama based
        summary = await workflow.execute_activity(
            summarize_content,
            (transcript_text, filepath),
            start_to_close_timeout=timedelta(minutes=10)
        )

        # 4. Refresh Index
        await workflow.execute_activity(
            refresh_index,
            start_to_close_timeout=timedelta(minutes=2)
        )

        return {
            "status": "completed",
            "url": url,
            "filepath": filepath,
            "summary": summary
        }

@workflow.defn
class BatchProcessingWorkflow:
    @workflow.run
    async def run(self, params: tuple) -> dict:
        query, limit = params
        workflow.logger.info(f"Batch processing started for query: {query}, limit: {limit}")
        
        # 1. Search
        urls = await workflow.execute_activity(
            search_videos,
            (query, limit), # Pass as tuple
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        workflow.logger.info(f"Found {len(urls)} videos to process")
        
        # 2. Process each video (Child Workflows or Activities)
        # Using Child Workflows is better for parallelism and independent failure
        results = []
        for url in urls:
            try:
                # Fire and forget or wait? User didn't specify. 
                # Waiting allows us to return a report.
                # Running sequentially or parallel? Parallel is better.
                # But to avoid overloading GPU? Temporal manages queues.
                # Let's run sequentially in this workflow for simplicity OR 
                # execute_child_workflow returns a handle.
                
                # Let's do parallel
                handle = await workflow.start_child_workflow(
                    VideoProcessingWorkflow.run,
                    url,
                    id=f"video-{url.split('=')[-1] if '=' in url else url[-12:]}", # Safer ID
                    task_queue="video-processing-queue",
                    parent_close_policy=workflow.ParentClosePolicy.ABANDON
                )
                results.append(handle.id)
                workflow.logger.info(f"Started child workflow {handle.id} for {url}")
                
            except Exception as e:
                workflow.logger.error(f"Failed to start workflow for {url}: {e}")
                
        return {"status": "dispatched", "count": len(results), "workflow_ids": results}
