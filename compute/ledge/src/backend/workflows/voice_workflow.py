"""Voice Conversation Workflow - STT -> LLM -> TTS."""

from datetime import timedelta

from temporalio import workflow

from src.shared.models import (
    VoiceWorkflowInput,
    VoiceWorkflowOutput,
    STTRequest,
    STTResponse,
    LLMRequest,
    LLMResponse,
    TTSRequest,
    TTSResponse,
)
from src.backend.activities import stt_transcribe, tts_synthesize
from src.backend.activities.llm_activity import llm_generate


@workflow.defn
class VoiceConversationWorkflow:
    """
    Complete voice conversation workflow.
    
    Flow: Audio Input -> STT -> LLM -> TTS -> Audio Output
    
    All activities run on GPU worker (@gpu queue).
    """
    
    @workflow.run
    async def run(self, input_data: VoiceWorkflowInput) -> VoiceWorkflowOutput:
        start_time = workflow.now()
        
        stt_result: STTResponse = await workflow.execute_activity(
            stt_transcribe,
            STTRequest(audio_data=input_data.audio_data, language=input_data.language),
            start_to_close_timeout=timedelta(seconds=60),
        )
        
        workflow.logger.info(f"STT result: {stt_result.text[:100]}...")
        
        llm_result: LLMResponse = await workflow.execute_activity(
            llm_generate,
            LLMRequest(
                prompt=stt_result.text,
                system_prompt="You are a helpful assistant. Respond concisely.",
                max_tokens=256,
                temperature=0.7,
            ),
            start_to_close_timeout=timedelta(seconds=60),
        )
        
        workflow.logger.info(f"LLM result: {llm_result.text[:100]}...")
        
        tts_result: TTSResponse = await workflow.execute_activity(
            tts_synthesize,
            TTSRequest(
                text=llm_result.text,
                language=stt_result.language if stt_result.language in ["zh", "en"] else "en",
            ),
            start_to_close_timeout=timedelta(seconds=60),
        )
        
        workflow.logger.info(f"TTS result: {len(tts_result.audio_data)} bytes")
        
        total_duration = (workflow.now() - start_time).total_seconds()
        
        return VoiceWorkflowOutput(
            transcribed_text=stt_result.text,
            llm_response=llm_result.text,
            audio_response=tts_result.audio_data,
            total_duration_seconds=total_duration,
        )
