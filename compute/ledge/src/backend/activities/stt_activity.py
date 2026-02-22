"""STT Activity - Speech-to-Text using faster-whisper."""

from temporalio import activity

from src.shared import STTRequest, STTResponse, get_logger

logger = get_logger("stt_activity")
_MODEL_CACHE = {}


def _get_whisper_model(model_size: str):
    from faster_whisper import WhisperModel

    model = _MODEL_CACHE.get(model_size)
    if model is None:
        logger.info(f"Loading Whisper model: {model_size}")
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        _MODEL_CACHE[model_size] = model
    return model


@activity.defn
def stt_transcribe(request: STTRequest) -> STTResponse:
    """
    Transcribe audio to text using faster-whisper.
    
    This activity runs on GPU worker (@gpu queue).
    """
    logger.info(f"Starting STT transcription, audio size: {len(request.audio_data)} bytes")
    
    tmp_path = None
    try:
        import tempfile
        import time

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(request.audio_data)
            tmp_path = tmp.name

        model = _get_whisper_model(request.model_size)

        start_time = time.time()
        segments, info = model.transcribe(tmp_path, language=request.language)

        text = "".join(segment.text for segment in segments)
        duration = time.time() - start_time

        logger.info(f"STT completed: {len(text)} chars, {duration:.2f}s")

        return STTResponse(
            text=text.strip(),
            language=info.language,
            duration_seconds=duration,
            confidence=info.language_probability,
        )

    except Exception as e:
        logger.error(f"STT transcription failed: {e}")
        raise
    finally:
        if tmp_path:
            import os

            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
