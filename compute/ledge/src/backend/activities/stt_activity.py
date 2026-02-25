"""STT Activity - Speech-to-Text using faster-whisper."""

import os

from temporalio import activity

from src.shared import STTRequest, STTResponse, get_logger

logger = get_logger("stt_activity")
_MODEL_CACHE = {}


def _stt_fallback_enabled() -> bool:
    value = os.getenv("LEDGE_STT_FALLBACK_ENABLED", "1").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _fallback_transcription(request: STTRequest, audio_data: bytes, error: Exception) -> STTResponse:
    language = request.language or "en"
    text = f"stt fallback transcription ({language}, {len(audio_data)} bytes)"
    logger.warning(f"STT fallback enabled, returning synthetic transcription: {error}")
    return STTResponse(
        text=text,
        language=language,
        duration_seconds=0.0,
        confidence=0.0,
    )


def _load_audio_from_minio(bucket: str, object_name: str) -> bytes:
    from src.shared.minio_auth import create_minio_client

    client = create_minio_client()
    response = client.get_object(bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _resolve_audio_bytes(request: STTRequest) -> bytes:
    if request.audio_data:
        return request.audio_data
    if request.audio_bucket and request.audio_object:
        logger.info(
            f"Loading STT audio from MinIO: bucket={request.audio_bucket}, object={request.audio_object}"
        )
        return _load_audio_from_minio(request.audio_bucket, request.audio_object)
    raise ValueError("STTRequest must include audio_data or audio_bucket/audio_object")


def _stt_device_policy() -> str:
    value = os.getenv("LEDGE_STT_DEVICE", "auto").strip().lower()
    if value in {"auto", "cuda", "cpu"}:
        return value
    return "auto"


def _model_load_candidates(device_policy: str):
    if device_policy == "cpu":
        return (("cpu", "int8"),)
    if device_policy == "cuda":
        return (("cuda", "float16"), ("cpu", "int8"))
    return (("cuda", "float16"), ("cpu", "int8"))


def _get_whisper_model(model_size: str):
    from faster_whisper import WhisperModel

    model = _MODEL_CACHE.get(model_size)
    if model is None:
        device_policy = _stt_device_policy()
        logger.info(f"Loading Whisper model: {model_size} (device_policy={device_policy})")

        last_error = None
        for device, compute_type in _model_load_candidates(device_policy):
            try:
                model = WhisperModel(model_size, device=device, compute_type=compute_type)
                if device == "cpu" and device_policy != "cpu":
                    logger.warning(
                        "STT model load fell back to CPU after CUDA load failure"
                    )
                _MODEL_CACHE[model_size] = model
                return model
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Failed to load Whisper model on {device} ({compute_type}): {exc}"
                )

        if last_error:
            raise last_error
    return model


@activity.defn
def stt_transcribe(request: STTRequest) -> STTResponse:
    """
    Transcribe audio to text using faster-whisper.
    
    This activity runs on GPU worker (@gpu queue).
    """
    audio_data = _resolve_audio_bytes(request)
    logger.info(f"Starting STT transcription, audio size: {len(audio_data)} bytes")
    
    tmp_path = None
    try:
        import tempfile
        import time

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
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
        if _stt_fallback_enabled():
            return _fallback_transcription(request, audio_data, e)
        logger.error(f"STT transcription failed: {e}")
        raise
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
