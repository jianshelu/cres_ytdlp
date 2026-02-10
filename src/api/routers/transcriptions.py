"""
Transcriptions API router for combined keywords feature.

Provides endpoint for fetching videos with combined keywords and transcriptions.
"""

import logging
import os
import json
import asyncio
import re
from typing import List, Optional, Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from pathlib import Path
from minio.error import S3Error

from src.backend.services.llm_llamacpp import LlamaCppClient
from src.backend.services.keyword_service import KeywordExtractionService, Keyword
from src.backend.services.sentence_service import SentenceService
from src.backend.services.cache_minio import MinioTranscriptionsCache, build_source_hash
try:
    from pypinyin import lazy_pinyin
except Exception:  # pragma: no cover - optional fallback
    lazy_pinyin = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["transcriptions"])

# Initialize services
llm_client = LlamaCppClient(base_url=os.getenv("LLAMA_URL", "http://localhost:8081"))

keyword_service = KeywordExtractionService(llm_client)
sentence_service = SentenceService()
cache_service = MinioTranscriptionsCache()

# Models
class VideoTranscription(BaseModel):
    """Video with transcription and keywords."""
    videoId: str
    title: str
    transcription: str
    keywords: List[Keyword]
    videoPath: str = ""
    segments: List[dict] = Field(default_factory=list)

class CombinedData(BaseModel):
    """Combined keywords and sentence."""
    keywords: List[Keyword]
    sentence: str
    key_sentences: List[dict] = Field(default_factory=list)
    combined_video_url: str = ""
    recombined_sentence: bool = False
    sentence_version: str = ""

class MetaData(BaseModel):
    """Metadata about extraction."""
    llm: str
    replaceCount: int
    coverage: List[bool]
    cache: Literal["hit", "miss", "disabled"] = "disabled"

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


async def fetch_transcript_payload(json_path: str) -> dict:
    """Fetch transcript payload and return text + optional keyword hints/segments."""
    if not json_path:
        return {"text": "", "keywords": [], "segments": []}

    try:
        # Handle MinIO/public HTTP URLs
        if json_path.startswith("http"):
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(json_path)
                response.raise_for_status()
                data = response.json()
                return {
                    "text": data.get("text", "") or "",
                    "keywords": data.get("keywords", []) or [],
                    "segments": data.get("segments", []) or [],
                }

        # Handle local files
        json_path = json_path.replace('test_downloads/', 'downloads/')
        full_path = Path('web/public') / json_path
        if not full_path.exists():
            logger.warning(f"Transcript file not found: {full_path}")
            return {"text": "", "keywords": [], "segments": []}

        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                "text": data.get("text", "") or "",
                "keywords": data.get("keywords", []) or [],
                "segments": data.get("segments", []) or [],
            }
    except Exception as e:
        logger.error(f"Failed to fetch transcript payload from {json_path}: {e}")
        return {"text": "", "keywords": [], "segments": []}


def _query_slug(query: str) -> str:
    raw = (query or "").strip()
    if not raw:
        return "batch"

    candidate = raw
    if lazy_pinyin is not None:
        try:
            pinyin = "".join(lazy_pinyin(raw))
            if pinyin.strip():
                candidate = pinyin
        except Exception:
            pass

    candidate = candidate.lower()
    candidate = re.sub(r"\s+", "-", candidate)
    candidate = re.sub(r"[^a-z0-9\-_]", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_-")
    return candidate or "batch"


def _keywords_from_string_list(keyword_terms: List[str], transcript: str, top_n: int = 5) -> List[Keyword]:
    """Convert plain keyword terms into Keyword models with computed counts."""
    out: List[Keyword] = []
    seen = set()
    for i, term in enumerate(keyword_terms):
        norm = keyword_service.normalize_term(str(term))
        if not norm or norm in seen:
            continue
        if keyword_service.is_low_quality_term(norm):
            continue
        seen.add(norm)
        count = keyword_service.count_occurrences(norm, transcript)
        if count == 0:
            continue
        # Keep a deterministic decreasing score from source order.
        score = max(0.1, 1.0 - (i * 0.05))
        out.append(Keyword(term=norm, score=score, count=count))
        if len(out) >= top_n:
            break
    return out


def _fallback_combined_from_per_video(per_video_keywords: List[List[Keyword]], top_n: int = 5) -> List[Keyword]:
    """Aggregate per-video keywords into a deterministic combined top list."""
    agg = {}
    for kws in per_video_keywords:
        for kw in kws:
            if kw.term not in agg:
                agg[kw.term] = {"score": kw.score, "count": kw.count}
            else:
                agg[kw.term]["score"] = max(agg[kw.term]["score"], kw.score)
                agg[kw.term]["count"] += kw.count
    ranked = sorted(
        (Keyword(term=t, score=v["score"], count=v["count"]) for t, v in agg.items()),
        key=lambda k: (-k.score, -k.count, k.term),
    )
    return ranked[:top_n]


def _keywords_from_title(title: str, query: str, top_n: int = 5) -> List[Keyword]:
    """Extract simple fallback keywords from title when transcript keywords are sparse."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", (title or ""))
    out: List[Keyword] = []
    seen = set()
    for i, raw in enumerate(tokens):
        norm = keyword_service.normalize_term(raw)
        if not norm or norm in seen:
            continue
        if keyword_service.is_low_quality_term(norm):
            continue
        seen.add(norm)
        score = max(0.2, 0.9 - i * 0.06)
        out.append(Keyword(term=norm, score=score, count=1))
        if len(out) >= top_n:
            break
    out = keyword_service.filter_keywords_by_query_language(out, query)
    out = keyword_service.filter_low_quality_keywords(out)
    return out[:top_n]


def _finalize_keywords(
    keywords: List[Keyword],
    query: str,
    transcript: str,
    top_n: int = 5
) -> List[Keyword]:
    """Final pass: normalize, dedupe, apply quality/language filter, and bound size."""
    normalized: List[Keyword] = []
    seen = set()
    for kw in keywords:
        norm = keyword_service.normalize_term(kw.term)
        if not norm or norm in seen:
            continue
        if keyword_service.is_low_quality_term(norm):
            continue
        seen.add(norm)
        count = keyword_service.count_occurrences(norm, transcript) if transcript else kw.count
        normalized.append(Keyword(term=norm, score=kw.score, count=max(count, 1)))
    normalized = keyword_service.filter_keywords_by_query_language(normalized, query)
    normalized = keyword_service.filter_low_quality_keywords(normalized)
    return normalized[:top_n]


def _load_batch_combined_output(query: str) -> Optional[dict]:
    """Read batch combined output from MinIO when available."""
    keys = [
        f"queries/{_query_slug(query)}/combined/combined-output.json",
        f"process/batch-{_query_slug(query)}/combined-output.json",  # backward compatibility
    ]
    for key in keys:
        try:
            data = cache_service.client.get_object(cache_service.bucket, key)
            try:
                payload = data.read()
            finally:
                data.close()
                data.release_conn()
            parsed = json.loads(payload.decode("utf-8"))
            logger.info(f"Loaded batch combined output: {key}")
            return parsed
        except S3Error as e:
            if getattr(e, "code", "") in {"NoSuchKey", "NoSuchObject"}:
                continue
            logger.warning(f"Failed to read batch combined output {key}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Failed to parse batch combined output {key}: {e}")
            continue
    return None

# API endpoint
@router.get("/transcriptions", response_model=TranscriptionsResponse)
async def get_transcriptions_with_combined_keywords(
    query: str = Query(..., description="Search query keyword"),
    limit: int = Query(50, ge=1, le=50, description="Maximum number of videos to return")
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
        limit: Maximum number of videos (default: 50, max: 50)
        
    Returns:
        TranscriptionsResponse with videos, combined keywords, and metadata
    """
    try:
        # Load data
        all_videos = await load_data_json()
        
        if not all_videos:
            raise HTTPException(status_code=500, detail="Failed to load video data")
        
        # Filter videos by search_query field (matches frontend filtering logic)
        query_lc = query.lower()
        matching_videos = [
            video for video in all_videos
            if (video.get('search_query') or '').lower() == query_lc
        ]
        
        if not matching_videos:
            # Return empty result if no matches
            return TranscriptionsResponse(
                query=query,
                videos=[],
                combined=CombinedData(keywords=[], sentence="", key_sentences=[]),
                meta=MetaData(
                    llm="llama.cpp:Meta-Llama-3.1-8B",
                    replaceCount=0,
                    coverage=[],
                    cache="miss"
                )
            )
        
        # Limit to top N videos
        selected_videos = matching_videos[:limit]
        source_hash = build_source_hash(selected_videos, limit)

        cache_enabled = os.getenv("ENABLE_TRANSCRIPTIONS_CACHE", "true").lower() in {"1", "true", "yes"}
        if cache_enabled:
            cached = cache_service.get(query=query, limit=limit, source_hash=source_hash)
            if cached and isinstance(cached.get("response"), dict):
                response_obj = cached["response"]
                cached_combined = response_obj.get("combined", {}) if isinstance(response_obj, dict) else {}
                cached_key_sentences = cached_combined.get("key_sentences", []) if isinstance(cached_combined, dict) else []
                cached_sentence = cached_combined.get("sentence", "") if isinstance(cached_combined, dict) else ""
                cached_video_url = cached_combined.get("combined_video_url", "") if isinstance(cached_combined, dict) else ""
                # Compatibility guard: old cache entries may miss/empty key_sentences.
                # In that case, recompute once and refresh cache with structured key sentences.
                if (not isinstance(cached_key_sentences, list) or len(cached_key_sentences) == 0) and cached_sentence:
                    logger.info("Cached payload missing key_sentences, recomputing and refreshing cache")
                elif not str(cached_video_url or "").strip():
                    logger.info("Cached payload missing combined_video_url, recomputing and refreshing cache")
                else:
                    # Ensure cache field is always explicit on read.
                    if "meta" in response_obj and isinstance(response_obj["meta"], dict):
                        response_obj["meta"]["cache"] = "hit"
                    try:
                        return TranscriptionsResponse(**response_obj)
                    except Exception:
                        logger.warning("Cached transcriptions payload was invalid, recomputing", exc_info=True)
        
        # Fetch transcript payloads concurrently (text + optional keyword hints).
        payloads = await asyncio.gather(
            *(fetch_transcript_payload(video.get('json_path')) for video in selected_videos)
        )
        transcripts = [p.get("text", "") or "" for p in payloads]
        video_transcriptions = [
            {
                "videoId": v.get("video_path", "").split("/")[-1].replace(".webm", ""),
                "title": v.get("title", "Unknown"),
                "transcription": transcripts[i],
                "videoPath": (v.get("video_path", "") or "").replace("test_downloads/", "downloads/"),
                "segments": payloads[i].get("segments", []) or [],
            }
            for i, v in enumerate(selected_videos)
        ]

        # Build fast per-video keyword seeds from stored transcript JSON keywords.
        per_video_keywords: List[List[Keyword]] = [
            _keywords_from_string_list(payloads[i].get("keywords", []), transcripts[i], top_n=5)
            for i in range(len(payloads))
        ]
        combined_text = "\n\n---\n\n".join(transcripts)
        key_sentence_items: List[dict] = []
        combined_video_url = ""
        recombined_sentence = False
        sentence_version = ""

        # Fast path: reuse batch combined output if available for this query.
        batch_combined = _load_batch_combined_output(query)
        if batch_combined and isinstance(batch_combined.get("combined_keywords"), list):
            final_combined = []
            for kw in batch_combined.get("combined_keywords", []):
                try:
                    final_combined.append(Keyword(**kw))
                except Exception:
                    continue
            replace_count = int(batch_combined.get("replaceCount", 0) or 0)
            combined_sentence = batch_combined.get("combined_sentence", "") or ""
            key_sentence_items = batch_combined.get("key_sentences", []) or []
            if not isinstance(key_sentence_items, list):
                key_sentence_items = []
            combined_video_url = str(batch_combined.get("combined_video_url", "") or "")
            recombined_sentence = bool(batch_combined.get("recombined_sentence", False))
            sentence_version = str(batch_combined.get("combined_sentence_version", "") or "")
        else:
            # Fallback: extract combined keywords via LLM.
            try:
                combined_keywords = await asyncio.wait_for(
                    keyword_service.extract_combined_keywords(
                        query=query,
                        transcripts=transcripts,
                        k=50
                    ),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Combined keyword extraction timed out for query: {query}")
                combined_keywords = []

            # Fill missing per-video keywords with deterministic fallback (no LLM wait).
            missing_indices = [i for i, kws in enumerate(per_video_keywords) if not kws]
            if missing_indices:
                for idx in missing_indices:
                    per_video_keywords[idx] = keyword_service._fallback_keywords_from_text(
                        transcripts[idx],
                        k=5
                    )

            # Apply coverage compensation
            final_combined, replace_count = await keyword_service.apply_coverage_compensation(
                combined_keywords=combined_keywords,
                transcripts=transcripts,
                per_transcript_keywords=per_video_keywords
            )
            if not final_combined:
                final_combined = _fallback_combined_from_per_video(per_video_keywords, top_n=5)

            # Extract combined sentence
            combined_sentence = sentence_service.extract_combined_sentence_from_transcripts(
                transcripts=transcripts,
                keywords=[kw.term for kw in final_combined]
            )
            key_sentence_items = sentence_service.extract_key_sentence_items_from_transcripts(
                transcripts=transcripts,
                keywords=[kw.term for kw in final_combined],
                max_sentences=5,
            )

        # Enforce query-language-consistent keywords (e.g., Chinese query => Chinese keywords).
        final_combined = _finalize_keywords(final_combined, query, combined_text, top_n=5)
        if not final_combined:
            fallback_combined = _fallback_combined_from_per_video(per_video_keywords, top_n=5)
            final_combined = _finalize_keywords(fallback_combined, query, combined_text, top_n=5)
        if len(final_combined) < 5:
            supplement = _fallback_combined_from_per_video(per_video_keywords, top_n=20)
            merged = final_combined + supplement
            final_combined = _finalize_keywords(merged, query, combined_text, top_n=5)
        
        # Compute coverage per transcript (whether transcript is covered by any combined keyword)
        coverage = keyword_service.compute_coverage(final_combined, transcripts)
        coverage_bool = [
            any(transcript_idx in keyword_coverage for keyword_coverage in coverage)
            for transcript_idx in range(len(transcripts))
        ]
        
        # Build response
        videos_response = []
        for i, vid in enumerate(video_transcriptions):
            # Top 5 keywords for this video
            top_k = per_video_keywords[i][:] if i < len(per_video_keywords) else []
            top_k = _finalize_keywords(top_k, query, transcripts[i], top_n=5)
            if not top_k and i < len(per_video_keywords):
                fb = keyword_service._fallback_keywords_from_text(transcripts[i], k=15)
                top_k = _finalize_keywords(fb, query, transcripts[i], top_n=5)
            if len(top_k) < 5:
                title_kws = _keywords_from_title(vid["title"], query, top_n=8)
                top_k = _finalize_keywords(top_k + title_kws, query, transcripts[i], top_n=5)
            
            videos_response.append(VideoTranscription(
                videoId=vid['videoId'],
                title=vid['title'],
                transcription=vid['transcription'],
                keywords=top_k,
                videoPath=vid.get('videoPath', ''),
                segments=vid.get('segments', []),
            ))
        
        # Normalize key sentence items for stable frontend rendering/navigation.
        normalized_key_sentences = []
        for idx, item in enumerate(key_sentence_items):
            if not isinstance(item, dict):
                continue
            sentence = str(item.get("sentence", "")).strip()
            if not sentence:
                continue
            source_index = int(item.get("source_index", -1))
            source_title = ""
            if 0 <= source_index < len(video_transcriptions):
                source_title = video_transcriptions[source_index]["title"]
            normalized_key_sentences.append(
                {
                    "id": idx,
                    "sentence": sentence,
                    "keyword": str(item.get("keyword", "")).strip(),
                    "source_index": source_index,
                    "source_title": source_title,
                }
            )

        if not normalized_key_sentences and combined_sentence:
            # Backward-compatible fallback for old combined-output payloads.
            fallback_sentences = sentence_service.split_sentences(combined_sentence)
            for idx, sentence in enumerate(fallback_sentences[:5]):
                src_idx = -1
                normalized_sentence = sentence.lower().strip()
                if normalized_sentence:
                    src_idx = next(
                        (
                            i
                            for i, t in enumerate(transcripts)
                            if normalized_sentence in (t or "").lower()
                        ),
                        -1,
                    )
                source_title = video_transcriptions[src_idx]["title"] if 0 <= src_idx < len(video_transcriptions) else ""
                normalized_key_sentences.append(
                    {
                        "id": idx,
                        "sentence": sentence,
                        "keyword": "",
                        "source_index": src_idx,
                        "source_title": source_title,
                    }
                )

        response = TranscriptionsResponse(
            query=query,
            videos=videos_response,
            combined=CombinedData(
                keywords=final_combined[:5],
                sentence=combined_sentence,
                key_sentences=normalized_key_sentences[:5],
                combined_video_url=combined_video_url,
                recombined_sentence=recombined_sentence,
                sentence_version=sentence_version,
            ),
            meta=MetaData(
                llm="llama.cpp:Meta-Llama-3.1-8B",
                replaceCount=replace_count,
                coverage=coverage_bool,
                cache="miss" if cache_enabled else "disabled"
            )
        )
        if cache_enabled:
            try:
                cache_service.set(
                    query=query,
                    limit=limit,
                    source_hash=source_hash,
                    response_payload=response.model_dump(),
                    combined_transcription=combined_text,
                )
            except Exception:
                # Cache write should never break response.
                logger.warning("Failed to write transcriptions cache", exc_info=True)
        return response
    
    except Exception as e:
        logger.error(f"Error in get_transcriptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
