"""TTS Activity - Text-to-Speech using Coqui TTS."""

from temporalio import activity

from src.shared import TTSRequest, TTSResponse, get_logger

logger = get_logger("tts_activity")


def _fallback_tone_wav(text: str, sample_rate: int = 16000) -> bytes:
    import io
    import math
    import struct
    import wave

    duration = max(1.0, min(4.0, len(text) / 18.0))
    total_frames = int(sample_rate * duration)
    frequency = 440.0
    amplitude = 2000

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(total_frames):
            value = int(amplitude * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            wav_file.writeframesraw(struct.pack("<h", value))
    return buffer.getvalue()


@activity.defn
async def tts_synthesize(request: TTSRequest) -> TTSResponse:
    """
    Synthesize text to speech using Coqui TTS.
    
    This activity runs on GPU worker (@gpu queue).
    """
    activity.logger.info(f"Starting TTS synthesis, text length: {len(request.text)} chars")
    
    try:
        try:
            import importlib

            TTS = importlib.import_module("TTS.api").TTS
        except ModuleNotFoundError:
            logger.warning("Coqui TTS unavailable, returning fallback tone audio")
            sample_rate = 16000
            audio_data = _fallback_tone_wav(request.text, sample_rate=sample_rate)
            return TTSResponse(
                audio_data=audio_data,
                sample_rate=sample_rate,
                duration_seconds=len(audio_data) / (sample_rate * 2),
            )
        
        import time
        import tempfile
        
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name
        
        tts.tts_to_file(
            text=request.text,
            language=request.language,
            file_path=output_path,
            speed=request.speed,
        )
        
        with open(output_path, "rb") as f:
            audio_data = f.read()
        
        import os
        os.unlink(output_path)
        
        duration = time.time() - start_time
        
        logger.info(f"TTS completed: {len(audio_data)} bytes, {duration:.2f}s")
        
        audio_duration = len(audio_data) / 32000
        
        return TTSResponse(
            audio_data=audio_data,
            sample_rate=16000,
            duration_seconds=audio_duration,
        )
        
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise
