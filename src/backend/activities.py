from temporalio import activity
import asyncio
import yt_dlp
import whisper
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
        'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
        'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
    
    # Upload to MinIO
    client = get_minio_client()
    bucket_name = "videos"
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # Force strip directory
    object_name = filepath.replace('\\', '/').split('/')[-1]
    activity.logger.info(f"Uploading {object_name} to MinIO bucket {bucket_name}")
    
    client.fput_object(bucket_name, object_name, filepath)
    activity.logger.info(f"Uploaded {object_name} to MinIO bucket {bucket_name}")

    # Clean up local file 
    # os.remove(filepath) # Optional: keep for cache or debug, but strictly we should clean up if scaling
    
    return object_name

@activity.defn
def transcribe_video(object_name: str) -> str:
    activity.logger.info(f"Transcribing file input param: '{object_name}'")
    
    # Download from MinIO
    client = get_minio_client()
    bucket_name = "videos"
    download_dir = "web/public/downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir, exist_ok=True)
        
    local_path = os.path.join(download_dir, object_name)
    
    # Check if we need to download (idempotency or cache check could go here)
    if not os.path.exists(local_path):
        client.fget_object(bucket_name, object_name, local_path)

    # Attempting to use GPU as requested
    try:
        model = whisper.load_model("base", device="cuda")
        activity.logger.info("Whisper model loaded on device: CUDA (GPU)")
    except Exception as e:
        activity.logger.error(f"Failed to load on CUDA, falling back to CPU: {e}")
        model = whisper.load_model("base", device="cpu")
        activity.logger.info("Whisper model loaded on device: CPU")
        
    result = model.transcribe(local_path)
    
    # Save transcript locally (temp)
    base_name = os.path.splitext(object_name)[0]
    json_path = os.path.join(download_dir, f"{base_name}.json")
    
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    
    # Upload transcript to MinIO
    transcript_bucket = "transcripts"
    if not client.bucket_exists(transcript_bucket):
        client.make_bucket(transcript_bucket)
        
    client.fput_object(transcript_bucket, f"{base_name}.json", json_path)
        
    return result['text']

@activity.defn

async def summarize_content(params: tuple) -> dict:
    text, object_name = params
    activity.logger.info(f"Summarizing content for {object_name}")
    
    # Truncate text if too long for prompt context
    max_chars = 12000 
    input_text = text[:max_chars]
    
    prompt = f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are a helpful assistant. Result must be valid JSON with fields: 'summary' (string) and 'keywords' (list of strings).
    <|eot_id|><|start_header_id|>user<|end_header_id|>
    Summarize the transcript and extract 5 key topics/tags.
    
    TRANSCRIPT:
    {input_text}
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """
    
    payload = {
        "prompt": prompt,
        "n_predict": 512,
        "temperature": 0.4,
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
        response = requests.post("http://localhost:8081/completion", json=payload, timeout=600)
        response.raise_for_status()
        result = response.json()
        
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
    transcript_bucket = "transcripts"
    download_dir = "web/public/downloads"
    base_name = os.path.splitext(object_name)[0]
    json_filename = f"{base_name}.json"
    local_json_path = os.path.join(download_dir, json_filename)
    
    # Check if we need to fetch it (if worker is on different node/pod)
    if not os.path.exists(local_json_path):
        try:
             client.fget_object(transcript_bucket, json_filename, local_json_path)
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
        client.fput_object(transcript_bucket, json_filename, local_json_path)
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
                 
             # License check usually requires full extraction.
             # If we skip license check for speed, we might violate constraints?
             # Let's skip license check in this iteration for speed unless critical.
             # Re-implementing FULL logic from batch_process.py:
             # SKIPPING strict license check for now as requested ("loosened")
             
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
