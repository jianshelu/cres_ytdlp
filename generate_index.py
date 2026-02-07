import json
import os
import io
import urllib.parse
import re
from minio import Minio

# Config
OUTPUT_JSON = "web/src/data.json"
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS = "minioadmin"
MINIO_SECRET = "minioadmin"
SECURE = False
BUCKET_CRES = "cres"

URL_BASE = f"http://{MINIO_ENDPOINT}"

def get_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=SECURE
    )

def process_keywords_in_bucket(client, object_limit=None):
    # This might be expensive if we list everything again or if we process per item.
    # For now, let's keep the logic simple: We iterate the main loop, identify transcript keys,
    # and then process them.
    pass

def get_metadata_title(client, object_key):
    try:
        response = client.get_object(BUCKET_CRES, object_key)
        meta = json.load(response)
        response.close()
        response.release_conn()
        
        if isinstance(meta, dict) and 'title' in meta:
            return meta['title']
    except Exception:
        pass
    return None

def process_transcript(client, object_key):
    """
    Reads transcript, scores keywords, updates if needed, returns (summary, keywords).
    """
    summary = "Generated automatically"
    keywords = []
    
    try:
        response = client.get_object(BUCKET_CRES, object_key)
        data = json.load(response)
        response.close()
        response.release_conn()
        
        if 'summary' in data:
            summary = data['summary']

        if 'keywords' in data:
            # check structure / scoring
            keywords_list = []
            text_lower = data.get('text', '').lower()
            segments = data.get('segments', [])
            raw_keywords = data['keywords']
            dirty = False 

            for k in raw_keywords:
                word_str = ""
                if isinstance(k, str):
                    word_str = k
                    dirty = True
                elif isinstance(k, dict) and 'word' in k:
                    word_str = k['word']
                else:
                    continue
                
                clean_k = word_str.strip()
                if not clean_k: continue
                
                count = text_lower.count(clean_k.lower())
                
                if count >= 20: score = 5
                elif count >= 10: score = 4
                elif count >= 5: score = 3
                elif count >= 3: score = 2
                else: score = 1
                
                # Calculate start_time from segments
                start_time = 0
                for seg in segments:
                    # Use regex for precise match with word boundaries
                    # This avoids partial matches like "anti" in "antigravity" if the keyword is just "anti"
                    pattern = re.compile(rf'\b{re.escape(clean_k)}\b', re.IGNORECASE)
                    if pattern.search(seg.get('text', '')):
                        start_time = seg.get('start', 0)
                        break
                
                keywords_list.append({"word": clean_k, "count": count, "score": score, "start_time": start_time})
            
            # Sort by score (desc), then count (desc) and take top 5
            keywords_list.sort(key=lambda x: (x['score'], x['count']), reverse=True)
            keywords_list = keywords_list[:5]

            if dirty:
                 data['keywords'] = keywords_list
                 new_content = json.dumps(data, indent=4, ensure_ascii=False).encode('utf-8')
                 client.put_object(
                     BUCKET_CRES, 
                     object_key, 
                     io.BytesIO(new_content), 
                     len(new_content),
                     content_type="application/json"
                 )
                 keywords = keywords_list
            else:
                keywords = keywords_list # Already structured
                
    except Exception as e:
        print(f"Error processing transcript {object_key}: {e}")

    return summary, keywords

def generate_index():
    client = get_minio_client()
    
    if not client.bucket_exists(BUCKET_CRES):
        print(f"Bucket {BUCKET_CRES} does not exist.")
        return

    objects = client.list_objects(BUCKET_CRES, recursive=True)
    
    entries_map = {}
    # entry structure: { 'video': key, 'thumb': key, 'meta': key, 'transcript': key }
    
    video_extensions = ('.mp4', '.webm', '.mkv', '.avi', '.mov')
    image_extensions = ('.jpg', '.webp', '.png', '.jpeg')

    for obj in objects:
        key = obj.object_name # e.g. "videos/Title_ID.mp4"
        
        parts = key.split('/')
        if len(parts) < 2:
            continue
            
        folder = parts[0]
        filename = parts[1]
        
        # Base name extraction
        # Special case: metadata is .info.json
        if filename.endswith('.info.json'):
            base = filename[:-10]
        else:
            base = os.path.splitext(filename)[0]
            
        if base not in entries_map:
            entries_map[base] = {'video': None, 'thumb': None, 'meta': None, 'transcript': None}
            
        if folder == 'videos':
            if filename.endswith('.info.json'):
                entries_map[base]['meta'] = key
            elif filename.lower().endswith(video_extensions):
                entries_map[base]['video'] = key
                
        elif folder == 'thumbnails':
             if filename.lower().endswith(image_extensions):
                 entries_map[base]['thumb'] = key
                 
        elif folder == 'transcripts':
             if filename.endswith('.json'):
                 entries_map[base]['transcript'] = key

    data = []
    
    for base_name, assets in entries_map.items():
        video_key = assets['video']
        if not video_key:
            continue
            
        thumb_key = assets['thumb']
        meta_key = assets['meta']
        transcript_key = assets['transcript']
        
        # 1. Title
        real_title = base_name
        if meta_key:
             t = get_metadata_title(client, meta_key)
             if t: real_title = t
             
        # 2. Transcript Info
        keywords = []
        summary = "Generated automatically"
        if transcript_key:
            s, k = process_transcript(client, transcript_key)
            summary = s
            keywords = k
            
        # Encode keys for URLs
        enc_video = urllib.parse.quote(video_key) if video_key else None
        enc_thumb = urllib.parse.quote(thumb_key) if thumb_key else None
        enc_trans = urllib.parse.quote(transcript_key) if transcript_key else None

        entry = {
            "title": real_title,
            "video_path": f"{URL_BASE}/{BUCKET_CRES}/{enc_video}",
            "thumb_path": f"{URL_BASE}/{BUCKET_CRES}/{enc_thumb}" if enc_thumb else None,
            "json_path": f"{URL_BASE}/{BUCKET_CRES}/{enc_trans}" if enc_trans else None,
            "keywords": keywords,
            "summary": summary
        }
        data.append(entry)

    data.sort(key=lambda x: x['title'])
    
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Index generated from {BUCKET_CRES}: {OUTPUT_JSON} with {len(data)} entries.")

if __name__ == "__main__":
    generate_index()
