from temporalio import activity
import asyncio
import yt_dlp
import os
import json
import errno
import requests
import re
import sys
import threading
from dataclasses import dataclass
from minio import Minio
from io import BytesIO
from datetime import timedelta, datetime
from yt_dlp.utils import DownloadError
try:
    from pypinyin import lazy_pinyin
except Exception:  # pragma: no cover - optional fallback
    lazy_pinyin = None

@dataclass
class VideoInfo:
    url: str
    title: str
    filepath: str
    duration: float


_WHISPER_MODEL_CACHE = {}
_WHISPER_MODEL_LOCK = threading.Lock()
_LOCAL_DOWNLOAD_ROOT = "web/public/downloads"


def _cleanup_local_temp_files(root: str = _LOCAL_DOWNLOAD_ROOT) -> int:
    """
    Best-effort cleanup for stale temp artifacts left by yt-dlp / MinIO partial uploads.
    Returns number of removed files.
    """
    removed = 0
    suffixes = (".part", ".part.minio", ".ytdl", ".tmp")
    if not os.path.isdir(root):
        return 0

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not name.endswith(suffixes):
                continue
            file_path = os.path.join(dirpath, name)
            try:
                os.remove(file_path)
                removed += 1
            except Exception:
                pass

    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        if dirnames or filenames:
            continue
        try:
            os.rmdir(dirpath)
        except Exception:
            pass

    return removed

def get_minio_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    secure = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


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


def _extract_query_slug_from_object_key(object_key: str) -> str | None:
    m = re.match(r"^queries/([^/]+)/", (object_key or ""))
    return m.group(1) if m else None


def _query_prefix(query: str) -> str:
    return f"queries/{_query_slug(query)}"


def _key_for_query(query: str, category: str, filename: str) -> str:
    return f"{_query_prefix(query)}/{category}/{filename}"


def _legacy_transcript_key_from_video_key(video_key: str) -> str:
    base_filename = os.path.basename(video_key or "")
    base_name_no_ext = os.path.splitext(base_filename)[0]
    return f"transcripts/{base_name_no_ext}.json"


def _transcript_key_from_video_key(video_key: str) -> str:
    slug = _extract_query_slug_from_object_key(video_key or "")
    base_filename = os.path.basename(video_key or "")
    base_name_no_ext = os.path.splitext(base_filename)[0]
    if slug:
        return f"queries/{slug}/transcripts/{base_name_no_ext}.json"
    return _legacy_transcript_key_from_video_key(video_key)


def _combined_output_key(query: str) -> str:
    return f"{_query_prefix(query)}/combined/combined-output.json"


def _manifest_key(query: str) -> str:
    return f"{_query_prefix(query)}/manifest.json"


def _upsert_query_manifest(client: Minio, bucket_name: str, query: str, update: dict) -> None:
    """Upsert manifest at queries/<slug>/manifest.json."""
    key = _manifest_key(query)
    payload = {
        "query": query,
        "slug": _query_slug(query),
        "videos": [],
        "combined": {},
    }
    try:
        obj = client.get_object(bucket_name, key)
        try:
            existing = json.loads(obj.read().decode("utf-8"))
            if isinstance(existing, dict):
                payload.update(existing)
        finally:
            obj.close()
            obj.release_conn()
    except Exception:
        pass

    # Merge update shallowly + merge videos by object_key.
    if isinstance(update, dict):
        if "videos" in update and isinstance(update["videos"], list):
            existing_videos = payload.get("videos", [])
            if not isinstance(existing_videos, list):
                existing_videos = []
            by_key = {}
            for item in existing_videos:
                if isinstance(item, dict):
                    by_key[item.get("object_key")] = item
            for item in update["videos"]:
                if not isinstance(item, dict):
                    continue
                k = item.get("object_key")
                if not k:
                    continue
                merged = dict(by_key.get(k, {}))
                merged.update(item)
                by_key[k] = merged
            payload["videos"] = list(by_key.values())
        if "combined" in update and isinstance(update["combined"], dict):
            combined = payload.get("combined", {})
            if not isinstance(combined, dict):
                combined = {}
            combined.update(update["combined"])
            payload["combined"] = combined
        for k, v in update.items():
            if k in {"videos", "combined"}:
                continue
            payload[k] = v

    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    client.put_object(
        bucket_name,
        key,
        BytesIO(raw),
        length=len(raw),
        content_type="application/json",
    )


def _is_chinese_text(text: str) -> bool:
    sample = (text or "")[:800]
    if not sample:
        return False
    cjk = sum(1 for c in sample if "\u4e00" <= c <= "\u9fff")
    return cjk / max(len(sample), 1) > 0.25


def _split_sentences_simple(text: str) -> list[str]:
    parts = re.split(r"[.!?ã€‚ï¼ï¼Ÿ]+\s*", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def _fallback_keywords_from_text(text: str, is_chinese: bool, k: int = 5) -> list[str]:
    if not text:
        return []

    if is_chinese:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
        stop = {"æˆ‘ä»¬", "ä½ ä»¬", "ä»–ä»¬", "è¿™ä¸ª", "é‚£ä¸ª", "ä»¥åŠ", "å› ä¸º", "æ‰€ä»¥", "å¯ä»¥", "ä¸€ä¸ª", "æ²¡æœ‰"}
    else:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text.lower())
        stop = {
            "the", "and", "for", "that", "this", "with", "you", "your", "are", "was",
            "have", "has", "had", "from", "they", "their", "about", "there", "what",
            "when", "where", "which", "will", "would", "could", "should", "into",
            "just", "like", "more", "than", "then", "over", "very", "some", "such",
            "been", "being", "also", "but", "not", "its", "our", "out", "all", "can",
            "get", "got", "one", "two", "three", "how", "why", "who", "whom", "whose",
            "video", "today", "people", "thing", "things", "make", "made", "using",
        }

    counts = {}
    for t in tokens:
        if t in stop:
            continue
        counts[t] = counts.get(t, 0) + 1

    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return [term for term, _ in ranked[:k]]


def _fallback_summary_data(text: str, is_chinese: bool) -> dict:
    sentences = _split_sentences_simple(text)
    if sentences:
        summary = " ".join(sentences[:2]).strip()
    else:
        summary = (text or "").strip()

    if not summary:
        summary = "Summary unavailable."
    summary = summary[:480]

    keywords = _fallback_keywords_from_text(text, is_chinese, k=5)
    if len(keywords) < 3:
        if is_chinese:
            keywords = (keywords + ["å†…å®¹", "ä¸»é¢˜", "æ¦‚è¿°"])[:3]
        else:
            keywords = (keywords + ["general", "overview", "topic"])[:3]

    return {"summary": summary, "keywords": keywords[:5]}


def _sanitize_summary_data(raw: dict, text: str, is_chinese: bool) -> dict:
    summary = str(raw.get("summary", "")).strip() if isinstance(raw, dict) else ""
    keywords_raw = raw.get("keywords", []) if isinstance(raw, dict) else []
    keywords = [str(k).strip() for k in keywords_raw if str(k).strip()] if isinstance(keywords_raw, list) else []

    seen = set()
    filtered_keywords = []
    lowered_text = (text or "").lower()
    for kw in keywords:
        norm = kw.lower()
        if norm in seen:
            continue
        seen.add(norm)

        if is_chinese:
            if not _is_chinese_text(kw):
                continue
        else:
            cjk_ratio = sum(1 for c in kw if "\u4e00" <= c <= "\u9fff") / max(len(kw), 1)
            if cjk_ratio > 0.20:
                continue

        # Keep only keywords that appear in transcript text.
        if _is_chinese_text(kw):
            if kw not in text:
                continue
        elif norm not in lowered_text:
            continue

        filtered_keywords.append(kw)
        if len(filtered_keywords) >= 5:
            break

    keywords = filtered_keywords

    if not summary or len(summary) < 10:
        return _fallback_summary_data(text, is_chinese)

    summary_cjk_ratio = sum(1 for c in summary if "\u4e00" <= c <= "\u9fff") / max(len(summary), 1)
    if not is_chinese and summary_cjk_ratio > 0.20:
        return _fallback_summary_data(text, is_chinese)

    if len(keywords) < 3:
        keywords = _fallback_summary_data(text, is_chinese)["keywords"]

    return {"summary": summary[:1000], "keywords": keywords}


def _get_whisper_model():
    """
    Reuse faster-whisper model across activities to avoid per-activity cold start.
    """
    model_size = os.getenv("WHISPER_MODEL_SIZE", "base").strip() or "base"

    with _WHISPER_MODEL_LOCK:
        gpu_key = ("cuda", model_size)
        if gpu_key in _WHISPER_MODEL_CACHE:
            return _WHISPER_MODEL_CACHE[gpu_key], "CUDA (GPU)"

        cpu_key = ("cpu", model_size)
        if cpu_key in _WHISPER_MODEL_CACHE:
            return _WHISPER_MODEL_CACHE[cpu_key], "CPU"

        from faster_whisper import WhisperModel

        try:
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
            _WHISPER_MODEL_CACHE[gpu_key] = model
            return model, "CUDA (GPU)"
        except Exception as e:
            activity.logger.error(f"Failed to load faster-whisper on CUDA, falling back to CPU: {e}")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            _WHISPER_MODEL_CACHE[cpu_key] = model
            return model, "CPU"

# Re-using logic from original main.py but adapted for Activities

@activity.defn
def download_video(params) -> str:
    # Backward-compatible input: url string OR (url, search_query)
    if isinstance(params, (tuple, list)):
        url, search_query = params
    else:
        url = params
        search_query = None
    if not isinstance(url, str):
        raise TypeError(f"download_video expected URL string, got {type(url).__name__}: {url!r}")
    activity.logger.info(f"Downloading video from {url} (query: {search_query})")
    download_root = _LOCAL_DOWNLOAD_ROOT
    removed_temp = _cleanup_local_temp_files(download_root)
    if removed_temp:
        activity.logger.info(f"Pre-download temp cleanup removed {removed_temp} stale files")
    query_local_dir = None
    if search_query:
        query_local_dir = os.path.join(download_root, _query_prefix(search_query), "videos")
        os.makedirs(query_local_dir, exist_ok=True)
        outtmpl = f"{query_local_dir}/%(title)s_%(id)s.%(ext)s"
    else:
        os.makedirs(download_root, exist_ok=True)
        outtmpl = f"{download_root}/%(title)s_%(id)s.%(ext)s"

    base_opts = {
        'outtmpl': outtmpl,
        'writethumbnail': True,
        'writeinfojson': True,  # Save metadata for title extraction
        'noplaylist': True,
        'restrictfilenames': True,  # Force ASCII filenames
        'merge_output_format': 'mp4',  # Force MP4 for browser compatibility
        'quiet': False,  # Enable more logging to debug format issues
        'geo_bypass_country': 'US',  # Use USA region for YouTube content
    }

    # Ordered fallback profiles to avoid "Requested format is not available" failures.
    ydl_profiles = [
        {
            # Preferred constrained profile
            'format': 'bestvideo[height<=480]+bestaudio/bestvideo[height<=720]+bestaudio/bestvideo[height<=1080]+bestaudio/best[height<=480]/best[height<=720]/best[height<=1080]/best',
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        },
        {
            # Relaxed adaptive profile
            'format': 'bestvideo*+bestaudio/best',
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        },
        {
            # Last-resort progressive profile
            'format': 'best',
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        },
    ]


    # Add cookies if available (to bypass bot detection)
    cookie_path = "/workspace/cookies.txt"
    cookie_enabled = os.path.exists(cookie_path)
    if cookie_enabled:
        activity.logger.info(f"Using cookies from {cookie_path}")
    
    filepath = None
    object_name = None
    try:
        info_dict = None
        last_error = None

        for idx, profile in enumerate(ydl_profiles, start=1):
            ydl_opts = dict(base_opts)
            ydl_opts.update(profile)
            if cookie_enabled:
                ydl_opts['cookiefile'] = cookie_path

            activity.logger.info(f"yt-dlp attempt {idx} with format='{ydl_opts.get('format')}'")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Pre-check info to avoid downloading active live streams
                    info = ydl.extract_info(url, download=False)
                    live_status = info.get('live_status')
                    is_live = info.get('is_live')

                    # Skip active or upcoming live streams; allow recorded live ("was_live")
                    if is_live or live_status in {"is_live", "is_upcoming", "upcoming", "live"}:
                        activity.logger.warning(f"Video is an active/upcoming live stream (status: {live_status}), skipping: {url}")
                        raise Exception(f"Live streams (active/upcoming) are not supported. Status: {live_status}")

                    info_dict = ydl.extract_info(url, download=True)
                    filepath = ydl.prepare_filename(info_dict)
                    break
            except DownloadError as e:
                last_error = e
                activity.logger.warning(f"yt-dlp attempt {idx} failed: {e}")
                continue

        if not info_dict or not filepath:
            raise last_error or Exception("yt-dlp failed with all format fallback profiles")

        # For MinIO, we want just the filename (e.g., "My Video_abc123.mp4")
        object_name = os.path.basename(filepath)

        # Upload video to MinIO
        client = get_minio_client()
        bucket_name = "cres"
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # Upload Main Video
        # object_name is just the filename here initially
        if search_query:
            video_key = _key_for_query(search_query, "videos", object_name)
        else:
            video_key = f"videos/{object_name}"
        client.fput_object(bucket_name, video_key, filepath)
        activity.logger.info(f"Uploaded {video_key} to MinIO bucket '{bucket_name}'")

        # Upload Sidecar Files (Thumbnail, InfoJson)
        base_name = os.path.splitext(filepath)[0]
        sidecar_scan_dir = os.path.dirname(filepath)
        for f in os.listdir(sidecar_scan_dir):
            full_f = os.path.join(sidecar_scan_dir, f)

            # Check if it starts with the base filename
            if f.startswith(os.path.basename(base_name)) and f != object_name:
                # Upload it
                # Determine prefix based on extension
                if f.endswith(('.jpg', '.webp', '.png')):
                    if search_query:
                        sidecar_key = _key_for_query(search_query, "thumbnails", f)
                    else:
                        sidecar_key = f"thumbnails/{f}"
                else:
                    # Assume metadata or other goes to videos
                    if search_query:
                        sidecar_key = _key_for_query(search_query, "videos", f)
                    else:
                        sidecar_key = f"videos/{f}"

                client.fput_object(bucket_name, sidecar_key, full_f)
                activity.logger.info(f"Uploaded sidecar {sidecar_key} to MinIO")
                # Delete sidecar
                os.remove(full_f)

    except Exception as e:
        activity.logger.error(f"Failed to download or upload video: {e}")
        # Clean up local file on failure as well
        if filepath and os.path.exists(filepath):
             os.remove(filepath)
        _cleanup_local_temp_files(download_root)
        raise

    # Clean up local file 
    if filepath and os.path.exists(filepath):
        os.remove(filepath)
        activity.logger.info(f"Deleted local file: {filepath}")
    _cleanup_local_temp_files(download_root)

    if search_query:
        _upsert_query_manifest(
            client,
            bucket_name,
            search_query,
            {
                "videos": [{
                    "object_key": video_key,
                    "url": url,
                    "status": "downloaded",
                }]
            }
        )

    return video_key

@activity.defn
def transcribe_video(object_name: str) -> str:
    activity.logger.info(f"Transcribing file input param: '{object_name}'")
    
    # Download from MinIO
    client = get_minio_client()
    bucket_name = "cres"
    download_dir = _LOCAL_DOWNLOAD_ROOT
    removed_temp = _cleanup_local_temp_files(download_dir)
    if removed_temp:
        activity.logger.info(f"Pre-transcribe temp cleanup removed {removed_temp} stale files")
    
    # object_name is now "videos/filename.mp4"
    local_path = os.path.join(download_dir, object_name)
    
    # Ensure local directory structure exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
    # Check if we need to download (idempotency or cache check could go here)
    if not os.path.exists(local_path):
        client.fget_object(bucket_name, object_name, local_path)

    model, model_device = _get_whisper_model()
    activity.logger.info(f"Faster-Whisper model loaded on device: {model_device}")
        
    segments, info = model.transcribe(local_path, beam_size=5)
    
    # Reconstruct result dict for compatibility with existing flow
    segments_list = []
    full_text = ""
    for segment in segments:
        segments_list.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        full_text += segment.text
    
    result = {
        "text": full_text,
        "segments": segments_list,
        "language": info.language
    }
    
    # Save transcript locally in query-scoped temp path to avoid cross-query filename collisions.
    transcript_key = _transcript_key_from_video_key(object_name)
    json_path = os.path.join(download_dir, transcript_key)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    try:
        with open(json_path, "w", encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
    except OSError as e:
        if e.errno == errno.ENOSPC:
            cleaned = _cleanup_local_temp_files(download_dir)
            activity.logger.warning(
                f"ENOSPC while writing transcript JSON; cleaned {cleaned} temp files and retrying once"
            )
            with open(json_path, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
        else:
            raise
    
    # Upload transcript to MinIO (query-scoped path if available).
    client.fput_object(bucket_name, transcript_key, json_path)
    
    # Cleanup local video copy
    if os.path.exists(local_path):
        os.remove(local_path)
        activity.logger.info(f"Deleted local video copy: {local_path}")

    # Cleanup local JSON transcript
    if os.path.exists(json_path):
        os.remove(json_path)
        activity.logger.info(f"Deleted local transcript: {json_path}")
    _cleanup_local_temp_files(download_dir)

    slug = _extract_query_slug_from_object_key(object_name)
    if slug:
        _upsert_query_manifest(
            client,
            bucket_name,
            slug,
            {
                "videos": [{
                    "object_key": object_name,
                    "transcript_key": transcript_key,
                    "status": "transcribed",
                }]
            }
        )
        
    return result['text']

@activity.defn
async def summarize_content(params: tuple) -> dict:
    if len(params) == 3:
        text, object_name, search_query = params
    else:
        text, object_name = params
        search_query = None
    activity.logger.info(f"Summarizing content for {object_name} (search_query: {search_query})")

    # Truncate text for prompt context
    max_chars = 12000
    input_text = text[:max_chars]
    is_chinese = _is_chinese_text(input_text)
    language_instruction = "Chinese" if is_chinese else "English"

    prompt = f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are a helpful assistant. Analyze the transcript and return concise JSON.

    CRITICAL:
    - Respond in {language_instruction} only. Do not switch language.
    - Return valid JSON only.
    - Provide 3-5 keyword terms.
    - Keywords must be terms from the transcript.

    JSON Format:
    {{
        "summary": "...",
        "keywords": ["...", "...", "..."]
    }}
    <|eot_id|><|start_header_id|>user<|end_header_id|>
    TRANSCRIPT:
    {input_text}
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """

    payload = {
        "prompt": prompt,
        "n_predict": 512,
        "temperature": 0.2,
        "repeat_penalty": 1.1,
        "json_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}}
            }
        }
    }

    summary_data = {"summary": "Failed", "keywords": []}

    try:
        activity.logger.info(f"LLM Prompt: {prompt[:500]}...")
        llm_base = os.getenv("LLAMA_URL", "http://localhost:8081").rstrip("/")
        response = requests.post(f"{llm_base}/completion", json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        activity.logger.info(f"LLM Raw Result: {json.dumps(result, ensure_ascii=False)}")

        content_str = result.get("content", "")
        try:
            parsed = json.loads(content_str)
        except json.JSONDecodeError:
            parsed = {"summary": content_str, "keywords": []}
        summary_data = _sanitize_summary_data(parsed, input_text, is_chinese)

    except Exception as e:
        activity.logger.error(f"Summarization failed: {e}")
        summary_data = _fallback_summary_data(input_text, is_chinese)

    # Add search_query to summary_data for storage
    if search_query:
        summary_data["search_query"] = search_query

    # Update the local/MinIO JSON file
    client = get_minio_client()
    bucket_name = "cres"
    download_dir = "web/public/downloads"

    base_filename = os.path.basename(object_name)
    base_name_no_ext = os.path.splitext(base_filename)[0]
    transcript_key = _transcript_key_from_video_key(object_name)
    local_json_path = os.path.join(download_dir, transcript_key)
    os.makedirs(os.path.dirname(local_json_path), exist_ok=True)

    if not os.path.exists(local_json_path):
        try:
            client.fget_object(bucket_name, transcript_key, local_json_path)
        except Exception as e:
            # Backward-compat: try legacy transcripts/<filename>.json when query-scoped key isn't present.
            legacy_key = _legacy_transcript_key_from_video_key(object_name)
            try:
                client.fget_object(bucket_name, legacy_key, local_json_path)
                transcript_key = legacy_key
            except Exception:
                activity.logger.error(f"Could not fetch existing transcript to update: {e}")
                return summary_data

    try:
        with open(local_json_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

        existing_data.update(summary_data)

        with open(local_json_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)

        client.fput_object(bucket_name, transcript_key, local_json_path)

        if os.path.exists(local_json_path):
            os.remove(local_json_path)
            activity.logger.info(f"Deleted local transcript: {local_json_path}")

    except Exception as e:
        activity.logger.error(f"Failed to update JSON artifact: {e}")

    if search_query:
        _upsert_query_manifest(
            client,
            bucket_name,
            search_query,
            {
                "videos": [{
                    "object_key": object_name,
                    "transcript_key": transcript_key,
                    "status": "summarized",
                    "search_query": search_query,
                    "summary_updated": True,
                }]
            }
        )

    return summary_data

@activity.defn
async def search_videos(params: tuple) -> list:
    if isinstance(params, (tuple, list)) and len(params) >= 4:
        query, limit, max_duration_minutes, max_age_days = params[0], params[1], params[2], params[3]
    elif isinstance(params, (tuple, list)) and len(params) >= 3:
        query, limit, max_duration_minutes = params[0], params[1], params[2]
        max_age_days = int(os.getenv("YOUTUBE_MAX_AGE_DAYS", "0") or "0")
    else:
        query, limit = params
        max_duration_minutes = 10
        max_age_days = int(os.getenv("YOUTUBE_MAX_AGE_DAYS", "0") or "0")
    max_duration_seconds = max(60, int(max_duration_minutes) * 60)
    max_age_days = max(0, int(max_age_days))
    min_upload_date = None
    if max_age_days > 0:
        min_upload_date = (datetime.utcnow() - timedelta(days=max_age_days)).strftime("%Y%m%d")
    activity.logger.info(
        f"Searching for videos with query: {query}, limit: {limit}, max_duration_minutes: {max_duration_minutes}, max_age_days: {max_age_days}"
    )
    
    ydl_opts = {
        'quiet': True, 
        'extract_flat': True, 
        'dump_single_json': True,
        'geo_bypass_country': 'US', # Use USA region for YouTube search
    }

    
    # Add cookies if available
    cookie_path = "/workspace/cookies.txt"
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    
    candidates = []
    # Over-fetch candidates because duration/live/url-type filters can drop many entries.
    # Cap at 50 to keep search fast enough.
    candidate_count = min(max(limit * 10, limit + 5), 50)
    search_query = f"ytsearch{candidate_count}:{query}"
    
    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(search_query, download=False)
            if 'entries' in res:
                return res['entries']
        return []

    # Run in thread pool since yt-dlp is blocking
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        candidates = await loop.run_in_executor(executor, _search)

    # Filter by maximum duration only (configured from request).
    MAX_DURATION = max_duration_seconds
    # LICENSE_FILTER = "creative commons" # Loosened as per request
    
    valid_urls = []
    seen_urls = set()
    for cand in candidates:
        if len(valid_urls) >= limit:
            break
            
        # extract_flat sometimes doesn't give duration/license. 
        # We might need full info. But full info is slow for searching.
        # Let's assume we proceed with these or do a second pass. 
        # In batch_process.py, it did a second extract_info.
        # Let's just return the candidates and let the workflow handle them, 
        # OR do the filtering here (better for "Search Activity").
        
        # Let's do a lightweight filter if possible, otherwise just return the URL.
        # Original script did full info extraction for filter. That's heavy for an activity 
        # but okay if limit is small. Let's return URLs and let a separate "Filter" activity 
        # or the main loop handle it? No, keeping it robust: just return the URLs found.
        # The user's request is "download video numbers", implying "get N videos".
        # Let's try to do the filtering here.
        
        try:
            # Just basic check from flat info if available?
            # Often flat info has duration.
            dur = cand.get('duration')
            if dur and dur > MAX_DURATION:
                continue
            if min_upload_date:
                upload_date = str(cand.get("upload_date") or "").strip()
                if upload_date and upload_date < min_upload_date:
                    continue

            live_status = cand.get("live_status")
            if cand.get('is_live') or live_status in {"is_live", "is_upcoming", "upcoming", "live"}:
                continue

            # extract_flat may return id/url/webpage_url with varying formats.
            # Keep only concrete YouTube watch URLs to avoid channel/playlist downloads.
            video_id = (cand.get("id") or "").strip()
            webpage_url = (cand.get("webpage_url") or "").strip()
            raw_url = (cand.get("url") or "").strip()

            url = ""
            if webpage_url and "watch?v=" in webpage_url:
                url = webpage_url
            elif raw_url and "watch?v=" in raw_url:
                url = raw_url
            elif video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                url = f"https://www.youtube.com/watch?v={video_id}"
            elif raw_url and re.fullmatch(r"[A-Za-z0-9_-]{11}", raw_url):
                url = f"https://www.youtube.com/watch?v={raw_url}"

            if not url:
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)
            valid_urls.append(url)

        except Exception:
            continue
            
    activity.logger.info(f"Returning {len(valid_urls)} valid URLs for query='{query}' (requested={limit})")
    return valid_urls

@activity.defn
def refresh_index() -> str:
    activity.logger.info("Refreshing video index...")
    try:
        import subprocess
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        # Optional path: refresh index through external API endpoint.
        # Useful when web/data.json is hosted on a separate server.
        reindex_url = os.getenv("REINDEX_URL", "").strip()
        if reindex_url:
            resp = requests.post(reindex_url, timeout=20)
            resp.raise_for_status()
            payload = (resp.text or "remote reindex ok").strip()
            activity.logger.info(f"Index refreshed via REINDEX_URL: {payload[:600]}")
            return payload

        run_env = os.environ.copy()
        # Force explicit MinIO config for subprocess, preventing localhost fallback.
        run_env["MINIO_ENDPOINT"] = run_env.get("MINIO_ENDPOINT", "localhost:9000")
        run_env["MINIO_SECURE"] = run_env.get("MINIO_SECURE", "false")
        run_env["MINIO_ACCESS_KEY"] = run_env.get(
            "MINIO_ACCESS_KEY",
            run_env.get("AWS_ACCESS_KEY_ID", "minioadmin"),
        )
        run_env["MINIO_SECRET_KEY"] = run_env.get(
            "MINIO_SECRET_KEY",
            run_env.get("AWS_SECRET_ACCESS_KEY", "minioadmin"),
        )
        run_env["MINIO_PUBLIC_BASE_URL"] = run_env.get("MINIO_PUBLIC_BASE_URL", "")

        result = subprocess.run(
            [sys.executable, "generate_index.py"],
            cwd=project_root,
            env=run_env,
            capture_output=True,
            text=True,
            check=True,
        )
        out = (result.stdout or result.stderr or "index refreshed").strip()
        activity.logger.info(f"Index refreshed: {out[:1200]}")
        return out
    except Exception as e:
        activity.logger.error(f"Failed to refresh index: {e}")
        return str(e)


@activity.defn
async def build_batch_combined_output(params: tuple) -> dict:
    """
    Build combined batch artifacts after child workflows complete and save to MinIO.
    Outputs include:
    - combined transcription
    - combined keyword tags
    - combined sentence
    """
    query, child_results = params
    activity.logger.info(f"Building batch combined output for query='{query}', child_count={len(child_results)}")

    from src.backend.services.llm_llamacpp import LlamaCppClient
    from src.backend.services.keyword_service import KeywordExtractionService, Keyword
    from src.backend.services.sentence_service import SentenceService

    client = get_minio_client()
    bucket_name = "cres"

    transcript_items = []
    transcripts = []

    # Gather transcript texts from MinIO based on child workflow outputs.
    for item in child_results:
        object_name = item.get("filepath") if isinstance(item, dict) else None  # e.g. videos/abc.mp4
        if not object_name:
            continue

        base_filename = os.path.basename(object_name)
        base_name_no_ext = os.path.splitext(base_filename)[0]
        transcript_key = _transcript_key_from_video_key(object_name)

        try:
            obj = client.get_object(bucket_name, transcript_key)
            try:
                payload = obj.read()
            finally:
                obj.close()
                obj.release_conn()
            data = json.loads(payload.decode("utf-8"))
            text = (data.get("text") or "").strip()
            if not text:
                continue
            transcripts.append(text)
            transcript_items.append({
                "video_object": object_name,
                "transcript_key": transcript_key,
                "text_len": len(text),
            })
        except Exception as e:
            legacy_key = _legacy_transcript_key_from_video_key(object_name)
            try:
                obj = client.get_object(bucket_name, legacy_key)
                try:
                    payload = obj.read()
                finally:
                    obj.close()
                    obj.release_conn()
                data = json.loads(payload.decode("utf-8"))
                text = (data.get("text") or "").strip()
                if not text:
                    continue
                transcripts.append(text)
                transcript_items.append({
                    "video_object": object_name,
                    "transcript_key": legacy_key,
                    "text_len": len(text),
                })
            except Exception:
                activity.logger.warning(f"Failed to load transcript '{transcript_key}': {e}")

    slug = _query_slug(query)
    object_key = _combined_output_key(query)
    combined_transcription_key = f"{_query_prefix(query)}/combined/combined-transcription.txt"
    combined_keywords_key = f"{_query_prefix(query)}/combined/combined-keywords.json"
    combined_sentence_key = f"{_query_prefix(query)}/combined/combined-sentence.txt"

    if not transcripts:
        payload = {
            "query": query,
            "count": 0,
            "replaceCount": 0,
            "transcripts": [],
            "combined_transcription": "",
            "combined_keywords": [],
            "combined_sentence": "",
            "key_sentences": [],
            "status": "no-transcripts",
        }
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        client.put_object(
            bucket_name,
            object_key,
            BytesIO(raw),
            length=len(raw),
            content_type="application/json",
        )
        activity.logger.info(f"Saved empty batch combined output to MinIO: {object_key}")
        _upsert_query_manifest(
            client,
            bucket_name,
            query,
            {
                "combined": {
                    "status": "no-transcripts",
                    "combined_output_key": object_key,
                }
            }
        )
        return {
            "status": "no-transcripts",
            "query": query,
            "count": 0,
            "object_key": object_key,
            "replaceCount": 0,
            "combined_keyword_count": 0,
            "combined_sentence_len": 0,
        }

    combined_text = "\n\n---\n\n".join(transcripts)

    # Build combined keywords/sentence using the same services used by /api/transcriptions.
    llm_client = LlamaCppClient(base_url=os.getenv("LLAMA_URL", "http://localhost:8081"))
    keyword_service = KeywordExtractionService(llm_client)
    sentence_service = SentenceService()

    try:
        combined_keywords = await asyncio.wait_for(
            keyword_service.extract_combined_keywords(query=query, transcripts=transcripts, k=50),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        combined_keywords = []

    async def _extract_single(transcript: str):
        try:
            return await asyncio.wait_for(
                keyword_service.extract_single_keywords(query=query, transcript=transcript, k=30),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            return []

    per_video_keywords = await asyncio.gather(*(_extract_single(t) for t in transcripts))
    final_combined, replace_count = await keyword_service.apply_coverage_compensation(
        combined_keywords=combined_keywords,
        transcripts=transcripts,
        per_transcript_keywords=per_video_keywords,
    )
    final_combined = keyword_service.filter_keywords_by_query_language(final_combined, query)
    final_combined = keyword_service.filter_low_quality_keywords(final_combined)
    if not final_combined:
        # Rebuild deterministic combined list from per-video keywords when filtered result becomes empty.
        agg = {}
        for kws in per_video_keywords:
            for kw in kws:
                if keyword_service.is_low_quality_term(kw.term):
                    continue
                if kw.term not in agg:
                    agg[kw.term] = {"score": kw.score, "count": kw.count}
                else:
                    agg[kw.term]["score"] = max(agg[kw.term]["score"], kw.score)
                    agg[kw.term]["count"] += kw.count
        fallback = sorted(
            (Keyword(term=t, score=v["score"], count=v["count"]) for t, v in agg.items()),
            key=lambda k: (-k.score, -k.count, k.term),
        )
        fallback = keyword_service.filter_keywords_by_query_language(fallback, query)
        final_combined = keyword_service.filter_low_quality_keywords(fallback)

    top_keywords = final_combined[:5]
    key_sentence_items = sentence_service.extract_key_sentence_items_from_transcripts(
        transcripts=transcripts,
        keywords=[kw.term for kw in top_keywords],
        max_sentences=5,
    )
    combined_sentence = sentence_service.extract_combined_sentence_from_transcripts(
        transcripts=transcripts,
        keywords=[kw.term for kw in top_keywords],
    )

    structured_key_sentences = []
    for item in key_sentence_items:
        src_idx = int(item.get("source_index", -1))
        src_video_object = ""
        if 0 <= src_idx < len(transcript_items):
            src_video_object = transcript_items[src_idx].get("video_object", "")
        structured_key_sentences.append(
            {
                "sentence": item.get("sentence", ""),
                "keyword": item.get("keyword", ""),
                "source_index": src_idx,
                "source_video_object": src_video_object,
            }
        )

    payload = {
        "query": query,
        "count": len(transcripts),
        "replaceCount": replace_count,
        "transcripts": transcript_items,
        "combined_transcription": combined_text,
        "combined_keywords": [kw.model_dump() for kw in top_keywords],
        "combined_sentence": combined_sentence,
        "key_sentences": structured_key_sentences,
    }

    # Save to MinIO process path.
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    client.put_object(
        bucket_name,
        object_key,
        BytesIO(raw),
        length=len(raw),
        content_type="application/json",
    )

    trans_raw = combined_text.encode("utf-8")
    client.put_object(
        bucket_name,
        combined_transcription_key,
        BytesIO(trans_raw),
        length=len(trans_raw),
        content_type="text/plain; charset=utf-8",
    )

    keywords_raw = json.dumps([kw.model_dump() for kw in top_keywords], ensure_ascii=False, indent=2).encode("utf-8")
    client.put_object(
        bucket_name,
        combined_keywords_key,
        BytesIO(keywords_raw),
        length=len(keywords_raw),
        content_type="application/json",
    )

    sentence_raw = (combined_sentence or "").encode("utf-8")
    client.put_object(
        bucket_name,
        combined_sentence_key,
        BytesIO(sentence_raw),
        length=len(sentence_raw),
        content_type="text/plain; charset=utf-8",
    )

    _upsert_query_manifest(
        client,
        bucket_name,
        query,
        {
            "combined": {
                "status": "ok",
                "combined_output_key": object_key,
                "combined_transcription_key": combined_transcription_key,
                "combined_keywords_key": combined_keywords_key,
                "combined_sentence_key": combined_sentence_key,
                "count": len(transcripts),
            }
        }
    )
    activity.logger.info(f"Saved batch combined output to MinIO: {object_key}")

    return {
        "status": "ok",
        "query": query,
        "count": len(transcripts),
        "object_key": object_key,
        "replaceCount": replace_count,
        "combined_keyword_count": len(top_keywords),
        "combined_sentence_len": len(combined_sentence),
    }
