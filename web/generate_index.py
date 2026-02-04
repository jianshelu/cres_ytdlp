import os
import json
import subprocess
import re
from collections import Counter

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
        
        text = data.get('text', '')
        # Simple regex to get words, lowercase them
        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Filter stop words
        filtered_words = [w for w in words if w not in STOP_WORDS]
        
        # Count frequencies
        counts = Counter(filtered_words)
        
        # Get top 10 keywords
        # FIX: Return simple strings to avoid React "Objects are not valid as a child" error
        top_keywords = [word for word, count in counts.most_common(10)]
        return top_keywords
    except Exception as e:
        print(f"Error extracting keywords from {json_path}: {e}")
        return []

def generate_index(download_dir="public/downloads", output_json="src/data.json"):
    if not os.path.exists(download_dir):
        print(f"Directory {download_dir} not found. Creating it.")
        os.makedirs(download_dir, exist_ok=True)

    video_extensions = ('.mp4', '.mkv', '.webm', '.avi', '.mov')
    files = os.listdir(download_dir)
    video_files = [f for f in files if f.lower().endswith(video_extensions)]
    
    data = []
    
    for video in video_files:
        video_path = os.path.join(download_dir, video)
        base_name = os.path.splitext(video)[0]
        json_path = os.path.join(download_dir, f"{base_name}.json")
        thumb_path = os.path.join(download_dir, f"{base_name}.jpg")
        
        # 1. Generate Thumbnail if missing
        if not os.path.exists(thumb_path):
            print(f"Generating thumbnail for {video}...")
            try:
                # Extract frame at 1 second mark
                subprocess.run([
                    'ffmpeg', '-y', '-i', video_path, 
                    '-ss', '00:00:01', '-vframes', '1', 
                    thumb_path
                ], check=True, capture_output=True)
            except Exception as e:
                print(f"Failed to generate thumbnail for {video}: {e}")
                thumb_path = None
        
        # 2. Check for JSON and extract keywords
        has_json = os.path.exists(json_path)
        keywords = extract_keywords(json_path) if has_json else []
        
        data.append({
            "title": base_name,
            # Fix path for web: must be relative to public, e.g. "downloads/video.webm"
            "video_path": f"downloads/{video}",
            "thumb_path": f"downloads/{base_name}.jpg" if thumb_path and os.path.exists(thumb_path) else None,
            "json_path": f"downloads/{base_name}.json" if has_json else None,
            "keywords": keywords,
            "summary": "Generated automatically" # Placeholder or extract from JSON if available?
        })
        
        # Try to extract summary from JSON if it exists
        if has_json:
             try:
                 with open(json_path, 'r', encoding='utf-8') as f:
                     jd = json.load(f)
                     if 'summary' in jd:
                         data[-1]['summary'] = jd['summary']
             except:
                 pass
    
    with open(output_json, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Index generated: {output_json} with {len(data)} entries.")

if __name__ == "__main__":
    generate_index()
