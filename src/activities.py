from temporalio import activity
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
    download_dir = "downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

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

    object_name = os.path.basename(filepath)
    client.fput_object(bucket_name, object_name, filepath)
    activity.logger.info(f"Uploaded {object_name} to MinIO bucket {bucket_name}")

    # Clean up local file 
    # os.remove(filepath) # Optional: keep for cache or debug, but strictly we should clean up if scaling
    
    return object_name

@activity.defn
def transcribe_video(object_name: str) -> str:
    activity.logger.info(f"Transcribing file: {object_name}")
    
    # Download from MinIO
    client = get_minio_client()
    bucket_name = "videos"
    download_dir = "downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    local_path = os.path.join(download_dir, object_name)
    
    # Check if we need to download (idempotency or cache check could go here)
    if not os.path.exists(local_path):
        client.fget_object(bucket_name, object_name, local_path)

    # Load model
    # Force CPU to avoid CUDA OOM in this shared env
    model = whisper.load_model("base", device="cpu") 
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
async def summarize_content(text: str) -> str:
    activity.logger.info("Summarizing content with llama.cpp")
    
    # Truncate text if too long for prompt context to avoid errors, 
    # though valid production approach handles chunking.
    # Llama 3.1 8B context is large (128k) but let's be safe/efficient.
    max_chars = 12000 
    input_text = text[:max_chars]
    
    prompt = f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are a helpful assistant efficiently summarizing video transcripts.
    <|eot_id|><|start_header_id|>user<|end_header_id|>
    Please summarize the following video transcript. Focus on key points and takeaways.
    
    TRANSCRIPT:
    {input_text}
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """
    
    payload = {
        "prompt": prompt,
        "n_predict": 512,
        "temperature": 0.7,
        "api_key": "not-needed" 
    }
    
    # Call local llama.cpp server
    try:
        response = requests.post("http://localhost:8081/completion", json=payload, timeout=600)
        response.raise_for_status()
        result = response.json()
        return result.get('content', '')
    except Exception as e:
        activity.logger.error(f"Summarization failed: {e}")
        return f"Summarization failed: {e}"
