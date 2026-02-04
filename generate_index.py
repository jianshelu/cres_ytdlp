import os
import json
import subprocess

# Config
DOWNLOAD_DIR = "web/public/downloads"
OUTPUT_JSON = "web/src/data.json"
URL_PREFIX = "downloads/"

def extract_keywords(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'keywords' in data:
                # Return list of objects {word, count}
                return [{"word": k, "count": data.get('text', '').lower().count(k.lower())} for k in data['keywords']]
    except Exception as e:
        print(f"Error extracting keywords from {json_path}: {e}")
    return []

def generate_index():
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Directory {DOWNLOAD_DIR} does not exist.")
        return

    files = os.listdir(DOWNLOAD_DIR)
    video_extensions = ('.mp4', '.webm', '.mkv', '.avi', '.mov')
    image_extensions = ('.jpg', '.webp', '.png', '.jpeg', '.JPG', '.PNG')
    
    # Map of base_name -> {video: None, thumb: None, json: None}
    entries_map = {}
    
    for f in files:
        if f in ['data.json', 'package.json', 'tsconfig.json']:
            continue
            
        base, ext = os.path.splitext(f)
        if base not in entries_map:
            entries_map[base] = {'video': None, 'thumb': None, 'json': None}
        
        if ext.lower() in video_extensions:
            entries_map[base]['video'] = f
        elif ext.lower() in image_extensions:
            entries_map[base]['thumb'] = f
        elif ext.lower() == '.json':
            entries_map[base]['json'] = f

    data = []
    
    for base_name, assets in entries_map.items():
        video_file = assets['video']
        thumb_filename = assets['thumb']
        json_filename = assets['json']
        
        full_video_path = os.path.join(DOWNLOAD_DIR, video_file) if video_file else None
        
        # 1. Generate Thumbnail if missing AND video exists
        if not thumb_filename and full_video_path and os.path.exists(full_video_path):
            print(f"Generating thumbnail for {base_name}...")
            # Try to use .jpg as default for generated
            gen_thumb_name = f"{base_name}.jpg"
            gen_thumb_path = os.path.join(DOWNLOAD_DIR, gen_thumb_name)
            try:
                subprocess.run([
                    'ffmpeg', '-y', '-i', full_video_path, 
                    '-ss', '00:00:01', '-vframes', '1', 
                    gen_thumb_path
                ], check=True, capture_output=True)
                thumb_filename = gen_thumb_name
            except Exception as e:
                print(f"Failed to generate thumbnail for {base_name}: {e}")
        
        # 2. Check for JSON and extract metadata
        keywords = []
        summary = "Generated automatically"
        if json_filename:
            full_json_path = os.path.join(DOWNLOAD_DIR, json_filename)
            keywords = extract_keywords(full_json_path)
            try:
                with open(full_json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    if isinstance(json_data, dict) and 'summary' in json_data:
                        summary = json_data['summary']
            except:
                pass
        
        # 3. Create Entry
        # Use existing video or assume .webm fallback for UI stability
        final_video_name = video_file if video_file else f"{base_name}.webm"
        
        entry = {
            "title": base_name,
            "video_path": f"{URL_PREFIX}{final_video_name}",
            "thumb_path": f"{URL_PREFIX}{thumb_filename}" if thumb_filename else None,
            "json_path": f"{URL_PREFIX}{json_filename}" if json_filename else None,
            "keywords": keywords,
            "summary": summary
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
