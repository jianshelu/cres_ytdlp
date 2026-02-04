import os
import json
import subprocess
import re
from collections import Counter

# Configuration
# Path to the directory containing video files (relative to project root or absolute)
DOWNLOAD_DIR = "web/public/downloads"
# Path where the output JSON should be saved
OUTPUT_JSON = "web/src/data.json"
# URL prefix for the web app (relative path from public/)
URL_PREFIX = "downloads/"

# Simple stop words list
STOP_WORDS = set([
    'the', 'and', 'a', 'to', 'of', 'in', 'is', 'it', 'you', 'that', 'this', 'for', 'on', 'with', 'as', 'are', 'was', 'be', 'at', 'or', 'an', 'have', 'from', 'but', 'not', 'by', 'we', 'he', 'she', 'they', 'our', 'their', 'my', 'me', 'us', 'him', 'her', 'them', 'if', 'will', 'can', 'just', 'all', 'so', 'about', 'some', 'no', 'up', 'down', 'out', 'into', 'over', 'now', 'then', 'when', 'where', 'how', 'why', 'what', 'which', 'who', 'get', 'got', 'go', 'going', 'been', 'has', 'had', 'do', 'does', 'did', 'doing', 'one', 'two', 'three', 'like', 'good', 'would', 'could', 'should', 'very', 'really', 'more', 'less', 'than', 'only', 'also', 'too', 'very', 'here', 'there', 'very', 'really'
])

def extract_keywords(json_path):
    if not json_path or not os.path.exists(json_path):
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        text = ""
        # Handle Whisper JSON format (segments) or raw text
        if isinstance(data, dict):
            if 'text' in data:
                text = data['text']
            elif 'segments' in data:
                text = " ".join([s.get('text', '') for s in data['segments']])
        elif isinstance(data, list):
            # List of segments
            text = " ".join([s.get('text', '') for s in data])
            
        # Simple regex to get words, lowercase them
        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Filter stop words
        filtered_words = [w for w in words if w not in STOP_WORDS]
        
        # Count frequencies
        counts = Counter(filtered_words)
        
        # Get top 10 keywords as objects
        top_keywords = [{"word": word, "count": count} for word, count in counts.most_common(10)]
        return top_keywords
    except Exception as e:
        print(f"Error extracting keywords from {json_path}: {e}")
        return []

def generate_index():
    # Ensure current directory is root or adjust paths 
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Directory {DOWNLOAD_DIR} not found. Please run from project root.")
        return

    video_extensions = ('.mp4', '.mkv', '.webm', '.avi', '.mov')
    files = os.listdir(DOWNLOAD_DIR)
    video_files = [f for f in files if f.lower().endswith(video_extensions)]
    
    data = []
    
    for video in video_files:
        full_video_path = os.path.join(DOWNLOAD_DIR, video)
        base_name = os.path.splitext(video)[0]
        
        # Paths relative to the public/downloads directory
        json_filename = f"{base_name}.json"
        thumb_filename = f"{base_name}.jpg"
        
        full_json_path = os.path.join(DOWNLOAD_DIR, json_filename)
        full_thumb_path = os.path.join(DOWNLOAD_DIR, thumb_filename)
        
        # 1. Generate Thumbnail if missing
        if not os.path.exists(full_thumb_path):
            print(f"Generating thumbnail for {video}...")
            try:
                subprocess.run([
                    'ffmpeg', '-y', '-i', full_video_path, 
                    '-ss', '00:00:01', '-vframes', '1', 
                    full_thumb_path
                ], check=True, capture_output=True)
            except Exception as e:
                print(f"Failed to generate thumbnail for {video}: {e}")
        
        # 2. Check for JSON and extract keywords
        has_json = os.path.exists(full_json_path)
        keywords = extract_keywords(full_json_path) if has_json else []
        
        # 3. Create Entry
        entry = {
            "title": base_name,
            # Web path: "downloads/video.mp4"
            "video_path": f"{URL_PREFIX}{video}",
            "thumb_path": f"{URL_PREFIX}{thumb_filename}" if os.path.exists(full_thumb_path) else None,
            "json_path": f"{URL_PREFIX}{json_filename}" if has_json else None,
            "keywords": keywords,
            "summary": "Generated automatically"
        }
        
        data.append(entry)
    
    # Sort by title
    data.sort(key=lambda x: x['title'])
    
    # Ensure output dir exists
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    
    with open(OUTPUT_JSON, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Index generated: {OUTPUT_JSON} with {len(data)} entries.")

if __name__ == "__main__":
    generate_index()
