"""
Transcriptions API router for combined keywords feature.

Provides endpoint for fetching videos with combined keywords and transcriptions.
"""

import logging
import os
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path

from src.backend.services.llm_llamacpp import LlamaCppClient
from src.backend.services.keyword_service import KeywordExtractionService, Keyword
from src.backend.services.sentence_service import SentenceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["transcriptions"])

# Initialize services
llm_client = LlamaCppClient(base_url=os.getenv("LLAMA_URL", "http://localhost:8080"))
keyword_service = KeywordExtractionService(llm_client)
sentence_service = SentenceService()

# Models
class VideoTranscription(BaseModel):
    """Video with transcription and keywords."""
    videoId: str
    title: str
    transcription: str
    keywords: List[Keyword]

class CombinedData(BaseModel):
    """Combined keywords and sentence."""
    keywords: List[Keyword]
    sentence: str

class MetaData(BaseModel):
    """Metadata about extraction."""
    llm: str
    replaceCount: int
    coverage: List[bool]

class TranscriptionsResponse(BaseModel):
    """Response for transcriptions endpoint."""
    query: str
    videos: List[VideoTranscription]
    combined: CombinedData
    meta: MetaData

# Helper functions
async def load_data_json() -> List[dict]:
    """Load data.json from web/src directory."""
    data_path = Path("web/src/data.json")
    if not data_path.exists():
        logger.error(f"data.json not found at {data_path}")
        return []
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load data.json: {e}")
        return []

async def fetch_transcript(json_path: str) -> Optional[str]:
    """Fetch transcript text from JSON file."""
    if not json_path:
        return None
    
    try:
        # Handle MinIO URLs (http://...)
        if json_path.startswith('http'):
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(json_path)
                response.raise_for_status()
                data = response.json()
                return data.get('text', '')
        
        # Handle local files
        json_path = json_path.replace('test_downloads/', 'downloads/')
        full_path = Path('web/public') / json_path
        
        if not full_path.exists():
            logger.warning(f"Transcript file not found: {full_path}")
            return None
        
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('text', '')
    
    except Exception as e:
        logger.error(f"Failed to fetch transcript from {json_path}: {e}")
        return None

# API endpoint
@router.get("/transcriptions", response_model=TranscriptionsResponse)
async def get_transcriptions_with_combined_keywords(
    query: str = Query(..., description="Search query keyword"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of videos to return")
):
    """
    Get transcriptions with combined keywords for a search query.
    
    This endpoint:
    1. Filters videos by query keyword (keyword must be in video's keyword list)
    2. Fetches transcripts for up to `limit` videos
    3. Extracts combined keywords using LLM from all transcriptions
    4. Applies coverage compensation to ensure each video is represented
    5. Generates combined sentence from keyword evidence sentences
    6. Returns videos with per-video keywords and combined data
    
    Args:
        query: Search query keyword
        limit: Maximum number of videos (default: 5, max: 10)
        
    Returns:
        TranscriptionsResponse with videos, combined keywords, and metadata
    """
    try:
        # Load data
        all_videos = await load_data_json()
        
        if not all_videos:
            raise HTTPException(status_code=500, detail="Failed to load video data")
        
        # Filter videos by query (case-insensitive keyword match)
        matching_videos = []
        for video in all_videos:
            keywords = video.get('keywords', [])
            if any(kw.get('word', '').lower() == query.lower() for kw in keywords):
                matching_videos.append(video)
        
        if not matching_videos:
            # Return empty result if no matches
            return TranscriptionsResponse(
                query=query,
                videos=[],
                combined=CombinedData(keywords=[], sentence=""),
                meta=MetaData(
                    llm="llama.cpp:Meta-Llama-3.1-8B",
                    replaceCount=0,
                    coverage=[]
                )
            )
        
        # Limit to top N videos
        selected_videos = matching_videos[:limit]
        
        # Fetch transcripts
        transcripts = []
        video_transcriptions = []
        
        for video in selected_videos:
            transcript_text = await fetch_transcript(video.get('json_path'))
            
            if not transcript_text:
                transcript_text = ""  # Fallback to empty if not found
            
            transcripts.append(transcript_text)
            video_transcriptions.append({
                'videoId': video.get('video_path', '').split('/')[-1].replace('.webm', ''),
                'title': video.get('title', 'Unknown'),
                'transcription': transcript_text
            })
        
        # Extract combined keywords (50 candidates from combined text)
        combined_keywords = await keyword_service.extract_combined_keywords(
            query=query,
            transcripts=transcripts,
            k=50
        )
        
        # Extract per-video keywords (30 candidates each)
        per_video_keywords = []
        for i, transcript in enumerate(transcripts):
            keywords = await keyword_service.extract_single_keywords(
                query=query,
                transcript=transcript,
                k=30
            )
            per_video_keywords.append(keywords)
        
        # Apply coverage compensation
        final_combined, replace_count = await keyword_service.apply_coverage_compensation(
            combined_keywords=combined_keywords,
            transcripts=transcripts,
            per_transcript_keywords=per_video_keywords
        )
        
        # Extract combined sentence
        combined_text = "\n\n---\n\n".join(transcripts)
        combined_sentence = sentence_service.extract_combined_sentence(
            combined_text=combined_text,
            keywords=[kw.term for kw in final_combined]
        )
        
        # Compute coverage
        coverage = keyword_service.compute_coverage(final_combined, transcripts)
        coverage_bool = [len(indices) > 0 for indices in coverage]
        
        # Build response
        videos_response = []
        for i, vid in enumerate(video_transcriptions):
            # Top 5 keywords for this video
            top_k = per_video_keywords[i][:5] if i < len(per_video_keywords) else []
            
            videos_response.append(VideoTranscription(
                videoId=vid['videoId'],
                title=vid['title'],
                transcription=vid['transcription'],
                keywords=top_k
            ))
        
        return TranscriptionsResponse(
            query=query,
            videos=videos_response,
            combined=CombinedData(
                keywords=final_combined[:5],
                sentence=combined_sentence
            ),
            meta=MetaData(
                llm="llama.cpp:Meta-Llama-3.1-8B",
                replaceCount=replace_count,
                coverage=coverage_bool
            )
        )
    
    except Exception as e:
        logger.error(f"Error in get_transcriptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
