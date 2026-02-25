"""TTS Activity - Text-to-Speech using Coqui TTS."""

import os

from temporalio import activity

from src.shared import MODEL_PATHS, TTSRequest, TTSResponse, get_logger

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

        tts_home = os.environ.get("TTS_HOME") or MODEL_PATHS["tts"]
        os.environ.setdefault("TTS_HOME", tts_home)
        os.makedirs(tts_home, exist_ok=True)

        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

        speaker = request.speaker
        if not speaker:
            speaker_manager = getattr(getattr(tts.synthesizer, "tts_model", None), "speaker_manager", None)
            available_speakers = list(getattr(speaker_manager, "name_to_id", []) or [])
            if available_speakers:
                speaker = available_speakers[0]

        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name
        
        tts.tts_to_file(
            text=request.text,
            language=request.language,
            speaker=speaker,
            file_path=output_path,
            speed=request.speed,
        )
        
        with open(output_path, "rb") as f:
            audio_data = f.read()
        
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
