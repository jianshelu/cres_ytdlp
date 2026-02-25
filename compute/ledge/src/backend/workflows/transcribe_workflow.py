"""Transcribe Workflow - STT only on GPU queue."""

from datetime import timedelta

from temporalio import workflow

from src.backend.activities import stt_transcribe
from src.shared.models import STTRequest, TranscribeWorkflowInput


@workflow.defn
class TranscribeWorkflow:
    """Workflow that performs STT only."""

    @workflow.run
    async def run(self, input_data: TranscribeWorkflowInput) -> dict:
        stt_result = await workflow.execute_activity(
            stt_transcribe,
            STTRequest(
                audio_data=input_data.audio_data,
                audio_bucket=input_data.audio_bucket,
                audio_object=input_data.audio_object,
                language=input_data.language,
            ),
            start_to_close_timeout=timedelta(seconds=240),
        )

        return {
            "text": stt_result.text,
            "language": stt_result.language,
            "duration_seconds": stt_result.duration_seconds,
            "confidence": stt_result.confidence,
        }
