from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities definition (only for type hinting in sandbox, 
# typically we use string names or stub proxies)
with workflow.unsafe.imports_passed_through():
    from activities import download_video, transcribe_video, summarize_content

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
            transcript_text,
            start_to_close_timeout=timedelta(minutes=10)
        )

        return {
            "status": "completed",
            "url": url,
            "filepath": filepath,
            "summary": summary
        }
