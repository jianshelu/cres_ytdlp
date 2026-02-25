"""STT endpoints for direct GPU access."""

from fastapi import APIRouter, HTTPException, UploadFile, File

from src.shared import STTRequest, STTResponse, get_logger

router = APIRouter()
logger = get_logger("stt_routes")


@router.post("/transcribe", response_model=STTResponse)
async def transcribe(
    audio: UploadFile = File(...),
    language: str | None = None,
    model_size: str = "/workspace/packages/models/whisperx/faster-whisper-large-v2",
):
    """
    Transcribe audio to text using faster-whisper (GPU).
    
    Direct access to Compute API, bypassing Temporal.
    """
    try:
        from faster_whisper import WhisperModel
        import tempfile
        import time
        
        audio_data = await audio.read()
        logger.info(f"Transcribing audio: {len(audio_data)} bytes")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        
        start_time = time.time()
        segments, info = model.transcribe(tmp_path, language=language)
        duration = time.time() - start_time
        
        text = "".join(segment.text for segment in segments)
        
        import os
        os.unlink(tmp_path)
        
        return STTResponse(
            text=text.strip(),
            language=info.language,
            duration_seconds=duration,
            confidence=info.language_probability,
        )
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
