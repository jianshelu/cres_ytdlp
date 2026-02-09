import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities definition (only for type hinting in sandbox, 
# typically we use string names or stub proxies)
with workflow.unsafe.imports_passed_through():
    from src.backend.activities import (
        download_video,
        transcribe_video,
        summarize_content,
        search_videos,
        refresh_index,
        build_batch_combined_output,
    )
    from pypinyin import lazy_pinyin


def _safe_query_slug(query: str) -> str:
    pinyin_slug = "".join(lazy_pinyin(query or ""))
    return pinyin_slug if pinyin_slug else "batch"


async def _run_query_pipeline_inline(
    query: str,
    limit: int,
    parallelism: int,
    max_duration_minutes: int,
) -> dict:
    """Execute full batch pipeline inline inside one workflow run."""
    urls = await workflow.execute_activity(
        search_videos,
        (query, limit, max_duration_minutes),
        start_to_close_timeout=timedelta(minutes=10),
    )
    workflow.logger.info(f"Found {len(urls)} videos to process (inline mode)")

    pipeline_ids = []
    completed_results = []
    failed_children = []
    safe_query = _safe_query_slug(query)

    def build_pipeline_id(idx: int, url: str) -> str:
        video_id = url.split("=")[-1] if "=" in url else url[-12:]
        return f"video-{safe_query}-{video_id}-{idx}"

    async def process_one(idx: int, url: str) -> dict:
        pipeline_id = build_pipeline_id(idx, url)
        pipeline_ids.append(pipeline_id)
        workflow.logger.info(f"Pipeline scheduled: {pipeline_id}")

        filepath = await workflow.execute_activity(
            download_video,
            (url, query),
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        transcript_text = await workflow.execute_activity(
            transcribe_video,
            filepath,
            start_to_close_timeout=timedelta(minutes=60),
        )
        summary = await workflow.execute_activity(
            summarize_content,
            (transcript_text, filepath, query),
            start_to_close_timeout=timedelta(minutes=10),
        )
        return {
            "status": "completed",
            "url": url,
            "workflow_id": pipeline_id,
            "filepath": filepath,
            "summary": summary,
            "search_query": query,
        }

    for start in range(0, len(urls), parallelism):
        chunk = urls[start:start + parallelism]
        chunk_meta = [
            (start + offset, url, build_pipeline_id(start + offset, url))
            for offset, url in enumerate(chunk)
        ]
        chunk_calls = [process_one(idx, url) for idx, url, _ in chunk_meta]
        chunk_results = await asyncio.gather(*chunk_calls, return_exceptions=True)
        for (_, url, pipeline_id), result in zip(chunk_meta, chunk_results):
            if isinstance(result, Exception):
                workflow.logger.error(f"Pipeline failed for {url}: {result}")
                failed_children.append(
                    {"workflow_id": pipeline_id, "url": url, "error": str(result)}
                )
            else:
                completed_results.append(result)
                workflow.logger.info(f"Pipeline completed: {pipeline_id}")

    combined_output = await workflow.execute_activity(
        build_batch_combined_output,
        (query, completed_results),
        start_to_close_timeout=timedelta(minutes=20),
        retry_policy=RetryPolicy(maximum_attempts=2),
    )
    await workflow.execute_activity(
        refresh_index,
        start_to_close_timeout=timedelta(minutes=2),
    )

    return {
        "status": "completed",
        "query": query,
        "parallelism": parallelism,
        "max_duration_minutes": max_duration_minutes,
        "dispatched_count": len(pipeline_ids),
        "completed_count": len(completed_results),
        "failed_count": len(failed_children),
        "workflow_ids": pipeline_ids,
        "failed_children": failed_children,
        "combined_output": combined_output,
    }

@workflow.defn
class VideoProcessingWorkflow:
    @workflow.run
    async def run(self, params: tuple) -> dict:
        # Temporal payload conversion may decode tuples as lists.
        # Accept both for backwards compatibility.
        if isinstance(params, (tuple, list)):
            url, search_query = params
        else:
            url = params
            search_query = None
            
        workflow.logger.info(f"Video processing workflow started for {url} (query: {search_query})")

        # 1. Download Activity
        # Retry logic: Retrying downloads is generally safe.
        filepath = await workflow.execute_activity(
            download_video,
            (url, search_query),
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
        # OpenAI/Llama based - pass search_query to be stored in metadata
        summary = await workflow.execute_activity(
            summarize_content,
            (transcript_text, filepath, search_query),
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
            "summary": summary,
            "search_query": search_query
        }

@workflow.defn
class BatchProcessingWorkflow:
    @workflow.run
    async def run(self, params: tuple) -> dict:
        if isinstance(params, (tuple, list)) and len(params) >= 4:
            query, limit, parallelism, max_duration_minutes = params[0], params[1], params[2], params[3]
        elif isinstance(params, (tuple, list)) and len(params) >= 3:
            query, limit, parallelism = params[0], params[1], params[2]
            max_duration_minutes = 10
        else:
            query, limit = params
            parallelism = 2
            max_duration_minutes = 10

        parallelism = max(1, min(4, int(parallelism)))
        max_duration_minutes = max(1, min(180, int(max_duration_minutes)))
        workflow.logger.info(
            f"Batch processing started for query: {query}, limit: {limit}, parallelism: {parallelism}, max_duration_minutes: {max_duration_minutes}"
        )
        
        return await _run_query_pipeline_inline(query, limit, parallelism, max_duration_minutes)


@workflow.defn
class QueryDispatcherWorkflow:
    def __init__(self) -> None:
        self._queue: list[dict] = []
        self._seen_order: list[str] = []
        self._seen_set: set[str] = set()
        self._processed_count = 0
        self._max_seen = 1000
        self._max_processed_before_continue = 100

    def _remember_request(self, request_id: str) -> None:
        if request_id in self._seen_set:
            return
        self._seen_set.add(request_id)
        self._seen_order.append(request_id)
        if len(self._seen_order) > self._max_seen:
            old = self._seen_order.pop(0)
            self._seen_set.discard(old)

    @workflow.signal
    def enqueue(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        request_id = str(payload.get("request_id", "")).strip()
        query = str(payload.get("query", "")).strip()
        if not request_id or not query:
            return
        if request_id in self._seen_set:
            return

        limit = max(1, min(50, int(payload.get("limit", 5))))
        parallelism = max(1, min(4, int(payload.get("parallelism", 2))))
        max_duration_minutes = max(1, min(180, int(payload.get("max_duration_minutes", 10))))

        self._queue.append(
            {
                "request_id": request_id,
                "query": query,
                "limit": limit,
                "parallelism": parallelism,
                "max_duration_minutes": max_duration_minutes,
            }
        )
        self._remember_request(request_id)

    @workflow.query
    def pending_count(self) -> int:
        return len(self._queue)

    @workflow.run
    async def run(self, initial_payload: dict | None = None) -> dict:
        if isinstance(initial_payload, dict):
            self.enqueue(initial_payload)

        while True:
            await workflow.wait_condition(lambda: len(self._queue) > 0)
            payload = self._queue.pop(0)
            query = payload["query"]
            limit = payload["limit"]
            parallelism = payload["parallelism"]
            max_duration_minutes = payload["max_duration_minutes"]
            request_id = payload["request_id"]

            pinyin_slug = "".join(lazy_pinyin(query))
            safe_query = pinyin_slug if pinyin_slug else "batch"
            suffix = request_id.replace("-", "")[:12]
            child_workflow_id = f"batch-{safe_query}-{suffix}"

            workflow.logger.info(
                f"Dispatcher starting batch child: {child_workflow_id}, query={query}, limit={limit}, parallelism={parallelism}, max_duration_minutes={max_duration_minutes}"
            )

            try:
                await workflow.execute_child_workflow(
                    BatchProcessingWorkflow.run,
                    (query, limit, parallelism, max_duration_minutes),
                    id=child_workflow_id,
                    task_queue="video-processing-queue",
                )
            except Exception as e:
                workflow.logger.error(f"Dispatcher child failed for query='{query}': {e}")

            self._processed_count += 1
            if self._processed_count >= self._max_processed_before_continue and not self._queue:
                workflow.logger.info("Dispatcher continue-as-new to compact workflow history")
                workflow.continue_as_new(None)


@workflow.defn
class QueryOrchestratorWorkflow:
    """
    New unified mode for testing:
    - single long-running orchestrator workflow
    - queue by signal
    - execute full video pipeline inline (no child BatchProcessingWorkflow)
    """

    def __init__(self) -> None:
        self._queue: list[dict] = []
        self._seen_order: list[str] = []
        self._seen_set: set[str] = set()
        self._processed_count = 0
        self._max_seen = 1000
        self._max_processed_before_continue = 100

    def _remember_request(self, request_id: str) -> None:
        if request_id in self._seen_set:
            return
        self._seen_set.add(request_id)
        self._seen_order.append(request_id)
        if len(self._seen_order) > self._max_seen:
            old = self._seen_order.pop(0)
            self._seen_set.discard(old)

    @workflow.signal
    def enqueue(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        request_id = str(payload.get("request_id", "")).strip()
        query = str(payload.get("query", "")).strip()
        if not request_id or not query:
            return
        if request_id in self._seen_set:
            return

        limit = max(1, min(50, int(payload.get("limit", 5))))
        parallelism = max(1, min(4, int(payload.get("parallelism", 2))))
        max_duration_minutes = max(1, min(180, int(payload.get("max_duration_minutes", 10))))

        self._queue.append(
            {
                "request_id": request_id,
                "query": query,
                "limit": limit,
                "parallelism": parallelism,
                "max_duration_minutes": max_duration_minutes,
            }
        )
        self._remember_request(request_id)

    @workflow.query
    def pending_count(self) -> int:
        return len(self._queue)

    @workflow.run
    async def run(self, initial_payload: dict | None = None) -> dict:
        if isinstance(initial_payload, dict):
            self.enqueue(initial_payload)

        while True:
            await workflow.wait_condition(lambda: len(self._queue) > 0)
            payload = self._queue.pop(0)
            query = payload["query"]
            limit = payload["limit"]
            parallelism = payload["parallelism"]
            max_duration_minutes = payload["max_duration_minutes"]
            request_id = payload["request_id"]

            workflow.logger.info(
                f"Orchestrator running inline pipeline: request_id={request_id}, query={query}, "
                f"limit={limit}, parallelism={parallelism}, max_duration_minutes={max_duration_minutes}"
            )
            try:
                await _run_query_pipeline_inline(query, limit, parallelism, max_duration_minutes)
            except Exception as e:
                workflow.logger.error(f"Orchestrator failed for query='{query}', request_id={request_id}: {e}")

            self._processed_count += 1
            if self._processed_count >= self._max_processed_before_continue and not self._queue:
                workflow.logger.info("Orchestrator continue-as-new to compact workflow history")
                workflow.continue_as_new(None)

@workflow.defn
class ReprocessVideoWorkflow:
    @workflow.run
    async def run(self, params: tuple) -> dict:
        text, object_name = params
        workflow.logger.info(f"Reprocessing keywords for {object_name}")
        
        # summary_data contains {summary, keywords}
        summary_data = await workflow.execute_activity(
            summarize_content,
            (text, object_name, None),  # No search query for reprocessing
            start_to_close_timeout=timedelta(minutes=10)
        )

        
        return summary_data
