"""TTS endpoints for direct GPU access."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.shared import TTSRequest, get_logger

router = APIRouter()
logger = get_logger("tts_routes")


@router.post("/synthesize")
async def synthesize(
    text: str,
    language: str = "zh",
    speaker: str = None,
    speed: float = 1.0,
):
    """
    Synthesize text to speech using Coqui TTS (GPU).
    
    Direct access to Compute API, bypassing Temporal.
    Returns audio/wav file.
    """
    try:
        from TTS.api import TTS
        import tempfile
        import time
        
        logger.info(f"Synthesizing text: {len(text)} chars")
        
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name
        
        tts.tts_to_file(
            text=text,
            language=language,
            file_path=output_path,
            speed=speed,
        )
        
        with open(output_path, "rb") as f:
            audio_data = f.read()
        
        import os
        os.unlink(output_path)
        
        duration = time.time() - start_time
        logger.info(f"TTS completed: {len(audio_data)} bytes, {duration:.2f}s")
        
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "X-Duration": str(duration),
            },
        )
        
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
