from temporalio import activity
import asyncio
import yt_dlp
import os
import json
import requests
from dataclasses import dataclass
from minio import Minio
from datetime import timedelta

@dataclass
class VideoInfo:
    url: str
    title: str
    filepath: str
    duration: float

def get_minio_client():
    return Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

# Re-using logic from original main.py but adapted for Activities

@activity.defn
def download_video(url: str) -> str:
    activity.logger.info(f"Downloading video from {url}")
    download_dir = "web/public/downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {
        # Prioritize Chinese audio (language matches 'zh' start), then fallback to best audio
        'format': 'bestvideo[height<=360]+bestaudio[language^=zh]/bestvideo[height<=360]+bestaudio/best[height<=360]',
        'outtmpl': f'{download_dir}/%(title)s_%(id)s.%(ext)s',
        'writethumbnail': True,
        'writeinfojson': True, # Save metadata for title extraction
        'noplaylist': True,
        'restrictfilenames': True, # Force ASCII filenames
        'merge_output_format': 'mp4', # Force MP4 for browser compatibility
    }

    # Add cookies if available (to bypass bot detection)
    cookie_path = "/workspace/cookies.txt"
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
        activity.logger.info(f"Using cookies from {cookie_path}")
    
    filepath = None
    object_name = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Pre-check info to avoid downloading active live streams
            info = ydl.extract_info(url, download=False)
            live_status = info.get('live_status')
            is_live = info.get('is_live')
            
            # If it's currently live or upcoming, we skip it
            if is_live and live_status != 'was_live':
                activity.logger.warning(f"Video is an active/upcoming live stream (status: {live_status}), skipping: {url}")
                raise Exception(f"Live streams (active/upcoming) are not supported. Status: {live_status}")
                
            info_dict = ydl.extract_info(url, download=True)
            # yt-dlp returns the actual filepath after download
            filepath = ydl.prepare_filename(info_dict)
            
            # For MinIO, we want just the filename (e.g., "My Video_abc123.mp4")
            object_name = os.path.basename(filepath)
            
            # Upload video to MinIO
            client = get_minio_client()
            bucket_name = "cres"
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
            
            # Upload Main Video
            # object_name is just the filename here initially
            video_key = f"videos/{object_name}" 
            client.fput_object(bucket_name, video_key, filepath)
            activity.logger.info(f"Uploaded {video_key} to MinIO bucket '{bucket_name}'")

            # Upload Sidecar Files (Thumbnail, InfoJson)
            base_name = os.path.splitext(filepath)[0] # e.g. web/public/downloads/Title_ID
            # List all files in download dir
            for f in os.listdir(download_dir):
                full_f = os.path.join(download_dir, f)
                
                # Check if it starts with the base filename
                if f.startswith(os.path.basename(base_name)) and f != object_name:
                    # Upload it
                    # Determine prefix based on extension
                    if f.endswith(('.jpg', '.webp', '.png')):
                        sidecar_key = f"thumbnails/{f}"
                    else:
                        # Assume metadata or other goes to videos
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
        raise

    # Clean up local file 
    if filepath and os.path.exists(filepath):
        os.remove(filepath)
        activity.logger.info(f"Deleted local file: {filepath}")
    
    return video_key

@activity.defn
def transcribe_video(object_name: str) -> str:
    activity.logger.info(f"Transcribing file input param: '{object_name}'")
    
    # Download from MinIO
    client = get_minio_client()
    bucket_name = "cres"
    download_dir = "web/public/downloads"
    
    # object_name is now "videos/filename.mp4"
    local_path = os.path.join(download_dir, object_name)
    
    # Ensure local directory structure exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
    # Check if we need to download (idempotency or cache check could go here)
    if not os.path.exists(local_path):
        client.fget_object(bucket_name, object_name, local_path)

    # Attempting to use GPU as requested with faster-whisper
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cuda", compute_type="float16")
        activity.logger.info("Faster-Whisper model loaded on device: CUDA (GPU)")
    except Exception as e:
        activity.logger.error(f"Failed to load on CUDA, falling back to CPU: {e}")
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        activity.logger.info("Faster-Whisper model loaded on device: CPU")
        
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
    
    # Save transcript locally (temp)
    # object_name = "videos/filename.mp4"
    # base = "filename.mp4"
    base_filename = os.path.basename(object_name)
    base_name_no_ext = os.path.splitext(base_filename)[0]
    
    # Save to a flat downloads dir or structured? 
    # Let's save flat to avoid deep nesting issues for temp files, or mirror
    # simpler: save flat in downloads dir
    json_path = os.path.join(download_dir, f"{base_name_no_ext}.json")
    
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    
    # Upload transcript to MinIO
    transcript_key = f"transcripts/{base_name_no_ext}.json"
        
    client.fput_object(bucket_name, transcript_key, json_path)
    
    # Cleanup local video copy
    if os.path.exists(local_path):
        os.remove(local_path)
        activity.logger.info(f"Deleted local video copy: {local_path}")

    # Cleanup local JSON transcript
    if os.path.exists(json_path):
        os.remove(json_path)
        activity.logger.info(f"Deleted local transcript: {json_path}")
        
    return result['text']

@activity.defn
async def summarize_content(params: tuple) -> dict:
    text, object_name = params
    activity.logger.info(f"Summarizing content for {object_name}")
    
    # Truncate text if too long for prompt context
    max_chars = 12000 
    input_text = text[:max_chars]
    
    # Detect language and enforce it in prompt
    # Simple heuristic: if >30% Chinese characters, it's Chinese
    chinese_chars = sum(1 for c in input_text[:500] if '\u4e00' <= c <= '\u9fff')
    is_chinese = chinese_chars > 150  # >30% of 500 chars
    
    language_instruction = "中文" if is_chinese else "the same language as the input"
    
    # Stronger prompt with explicit language enforcement
    prompt = f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are a helpful assistant. Analyzing the transcript below, provide a brief summary and keywords.
    
    CRITICAL: You MUST respond in {language_instruction}. If the transcript is in Chinese, the summary and keywords MUST be in Chinese.
    
    JSON Format (strictly 3-5 keywords):
    {{
        "summary": "...",
        "keywords": ["...", "...", "..."]
    }}
    <|eot_id|><|start_header_id|>user<|end_header_id|>
    TRANSCRIPT ({language_instruction}):
    {input_text}
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """
    
    payload = {
        "prompt": prompt,
        "n_predict": 512,
        "temperature": 0.3,  # Lower temperature for more consistent language matching
        "repeat_penalty": 1.1, # Prevent loops
        "json_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
    
    summary_data = {"summary": "Failed", "keywords": []}
    
    # Call local llama.cpp server
    try:
        activity.logger.info(f"LLM Prompt: {prompt[:500]}...") # Log start of prompt
        response = requests.post("http://localhost:8081/completion", json=payload, timeout=600)
        response.raise_for_status()
        result = response.json()
        activity.logger.info(f"LLM Raw Result: {json.dumps(result, ensure_ascii=False)}")
        
        content_str = result.get('content', '')
        try:
            summary_data = json.loads(content_str)
        except json.JSONDecodeError:
            summary_data = {"summary": content_str, "keywords": []}
            
    except Exception as e:
        activity.logger.error(f"Summarization failed: {e}")
        summary_data = {"summary": f"Summarization failed: {e}", "keywords": []}

    # Update the local/MinIO JSON file
    client = get_minio_client()
    bucket_name = "cres"
    download_dir = "web/public/downloads"
    
    # object_name comes from transcribe_video result? No, params usually "videos/abc.mp4"
    # Actually summarize takes (text, object_name) from previous steps?
    # Usually workflow passes the key.
    
    base_filename = os.path.basename(object_name)
    base_name_no_ext = os.path.splitext(base_filename)[0]
    json_filename = f"{base_name_no_ext}.json"
    transcript_key = f"transcripts/{json_filename}"
    
    local_json_path = os.path.join(download_dir, json_filename)
    
    # Check if we need to fetch it (if worker is on different node/pod)
    if not os.path.exists(local_json_path):
        try:
             client.fget_object(bucket_name, transcript_key, local_json_path)
        except Exception as e:
             activity.logger.error(f"Could not fetch existing transcript to update: {e}")
             return summary_data # Return partial

    # Update file
    try:
        with open(local_json_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        existing_data.update(summary_data)
        
        with open(local_json_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
            
        # Re-upload
        client.fput_object(bucket_name, transcript_key, local_json_path)
        
        # Cleanup
        if os.path.exists(local_json_path):
            os.remove(local_json_path)
            activity.logger.info(f"Deleted local transcript: {local_json_path}")
            
    except Exception as e:
        activity.logger.error(f"Failed to update JSON artifact: {e}")

    return summary_data

@activity.defn
async def search_videos(params: tuple) -> list:
    query, limit = params
    activity.logger.info(f"Searching for videos with query: {query}, limit: {limit}")
    
    ydl_opts = {
        'quiet': True, 
        'extract_flat': True, 
        'dump_single_json': True
    }
    
    # Add cookies if available
    cookie_path = "/workspace/cookies.txt"
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    
    candidates = []
    # Search slightly more than limit to account for filtering if we were filtering,
    # but for now we just return raw URLs and let workflow decide or loop filters.
    # Actually, let's filter here to match original logic if possible, or just return top N.
    # For simplicity/robustness, we fetch 2*limit candidates.
    search_query = f"ytsearch{limit*2}:{query}"
    
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

    # Filter (Basic duration filter matching batch_process.py)
    MIN_DURATION = 180
    MAX_DURATION = 1200 # Updated to 20 mins
    # LICENSE_FILTER = "creative commons" # Loosened as per request
    
    valid_urls = []
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
             if dur and not (MIN_DURATION <= dur <= MAX_DURATION):
                 continue
                 
             if cand.get('is_live'):
                 continue
                 
             url = cand.get('url')
             valid_urls.append(url)
             
        except Exception:
            continue
            
    return valid_urls

@activity.defn
def refresh_index() -> str:
    activity.logger.info("Refreshing video index...")
    try:
        import subprocess
        # Run generate_index.py from the root directory
        result = subprocess.run(["python3", "generate_index.py"], capture_output=True, text=True, check=True)
        activity.logger.info(f"Index refreshed: {result.stdout}")
        return result.stdout
    except Exception as e:
        activity.logger.error(f"Failed to refresh index: {e}")
        return str(e)
