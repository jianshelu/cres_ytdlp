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
        top_keywords = [{"word": word, "count": count} for word, count in counts.most_common(10)]
        return top_keywords
    except Exception as e:
        print(f"Error extracting keywords from {json_path}: {e}")
        return []

def generate_index(download_dir="test_downloads", output_json="data.json"):
    if not os.path.exists(download_dir):
        print(f"Directory {download_dir} not found.")
        return

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
            "video_path": video_path,
            "thumb_path": thumb_path if thumb_path and os.path.exists(thumb_path) else None,
            "json_path": json_path if has_json else None,
            "keywords": keywords
        })
    
    with open(output_json, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Index generated: {output_json} with {len(data)} entries.")

if __name__ == "__main__":
    generate_index()
