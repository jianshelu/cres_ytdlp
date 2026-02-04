import os
import yt_dlp
import whisper
import json
import re

DOWNLOAD_DIR = "/home/rama/cres_ytdlp/web/public/downloads"
TARGET_COUNT = 10
SEARCH_QUERY = "Google antigravity"

# Filters
MIN_DURATION = 180
MAX_DURATION = 900
LICENSE_FILTER = "creative commons"

def filter_video(info):
    duration = info.get('duration', 0)
    if not (MIN_DURATION <= duration <= MAX_DURATION):
        return False, f"Duration {duration}s"
    
    lic = info.get('license', '').lower()
    if LICENSE_FILTER not in lic:
        return False, f"License '{lic}'"
    
    return True, "OK"

def process():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    # 1. Search
    print(f"Searching for '{SEARCH_QUERY}'...")
    ydl_opts = {
        'quiet': True, 
        'extract_flat': True, 
        'dump_single_json': True
    }
    
    candidates = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Search more candidates to account for filtering
        res = ydl.extract_info(f"ytsearch200:{SEARCH_QUERY}", download=False)
        if 'entries' in res:
            candidates = res['entries']

    print(f"Found {len(candidates)} candidates.")
    
    # Check what we already have
    existing_jsons = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.json')]
    processed_count = len(existing_jsons)
    print(f"Already have {processed_count} videos.")
    
    # Load model once
    print("Loading Whisper model...")
    model = whisper.load_model("base")

    # 2. Iterate and Process
    for cand in candidates:
        if processed_count >= TARGET_COUNT:
            break
            
        url = cand.get('url')
        title = cand.get('title', 'Unknown')
        
        # Simple duplications check by title in filename roughly?
        # Better: check if we have a file with this title
        # Sanitize title for filename check (simplified)
        # But yt-dlp does specific sanitization. 
        # Easier: just check if we processed this URL? No we don't store URLs in a DB.
        # Proceed to check filter.
        
        print(f"Checking {title}...")
        
        # Get full info for filtering
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"Error fetching info: {e}")
            continue
            
        accepted, reason = filter_video(info)
        if not accepted:
            print(f"Skipped: {reason}")
            continue
            
        print(f"Accepted! Downloading...")
        
        # Download 360p
        dl_opts = {
            'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'noplaylist': True,
        }
        
        try:
            filename = ""
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            # Ensure filename matches reality (yt-dlp might merge exts)
            # Just find the file starting with title
            
            # Transcribe
            print(f"Transcribing {os.path.basename(filename)}...")
            result = model.transcribe(filename)
            
            # Save raw transcript
            base = os.path.splitext(os.path.basename(filename))[0]
            json_path = os.path.join(DOWNLOAD_DIR, f"{base}.json")
            
            with open(json_path, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            
            processed_count += 1
            print(f"Processed {processed_count}/{TARGET_COUNT}: {title}")
            
        except Exception as e:
            print(f"Error processing {url}: {e}")

    print("Batch processing complete.")

if __name__ == "__main__":
    process()
