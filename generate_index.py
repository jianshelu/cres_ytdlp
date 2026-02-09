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
    Reads transcript, scores keywords, updates if needed, returns (summary, keywords, search_query).
    """
    summary = "Generated automatically"
    keywords = []
    search_query = None
    
    try:
        response = client.get_object(BUCKET_CRES, object_key)
        data = json.load(response)
        response.close()
        response.release_conn()
        
        if 'summary' in data:
            summary = data['summary']

        if 'search_query' in data:
            search_query = data['search_query']

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

    return summary, keywords, search_query


def generate_index():
    client = get_minio_client()
    
    if not client.bucket_exists(BUCKET_CRES):
        print(f"Bucket {BUCKET_CRES} does not exist.")
        return

    objects = client.list_objects(BUCKET_CRES, recursive=True)
    
    entries_map = {}
    query_slug_latest_ts = {}
    query_slug_to_query_text = {}
    # entry structure: { 'video': key, 'thumb': key, 'meta': key, 'transcript': key }
    
    video_extensions = ('.mp4', '.webm', '.mkv', '.avi', '.mov')
    image_extensions = ('.jpg', '.webp', '.png', '.jpeg')

    for obj in objects:
        key = obj.object_name  # e.g. queries/oracle/videos/Title_ID.mp4 or videos/Title_ID.mp4
        parts = key.split('/')
        if len(parts) < 2:
            continue

        query_slug = None
        folder = parts[0]
        filename = parts[-1]
        if len(parts) >= 4 and parts[0] == "queries":
            query_slug = parts[1]
            folder = parts[2]
            lm = getattr(obj, "last_modified", None)
            if lm is not None:
                prev = query_slug_latest_ts.get(query_slug)
                if prev is None or lm > prev:
                    query_slug_latest_ts[query_slug] = lm

        if folder not in {"videos", "thumbnails", "transcripts"}:
            if len(parts) >= 3 and parts[0] == "queries" and parts[2] == "manifest.json":
                try:
                    obj_manifest = client.get_object(BUCKET_CRES, key)
                    try:
                        manifest = json.loads(obj_manifest.read().decode("utf-8"))
                    finally:
                        obj_manifest.close()
                        obj_manifest.release_conn()
                    q = (manifest.get("query") or "").strip()
                    q_slug = parts[1]
                    if q and q_slug:
                        query_slug_to_query_text[q_slug] = q
                except Exception:
                    pass
            continue

        # Base name extraction
        if filename.endswith('.info.json'):
            base = filename[:-10]
        else:
            base = os.path.splitext(filename)[0]

        entry_id = f"{query_slug or '_legacy'}::{base}"
        if entry_id not in entries_map:
            entries_map[entry_id] = {
                'video': None,
                'thumb': None,
                'meta': None,
                'transcript': None,
                'query_slug': query_slug,
            }

        if folder == 'videos':
            if filename.endswith('.info.json'):
                entries_map[entry_id]['meta'] = key
            elif filename.lower().endswith(video_extensions):
                entries_map[entry_id]['video'] = key
        elif folder == 'thumbnails':
            if filename.lower().endswith(image_extensions):
                entries_map[entry_id]['thumb'] = key
        elif folder == 'transcripts':
            if filename.endswith('.json'):
                entries_map[entry_id]['transcript'] = key

    data = []
    # Prefer query-scoped records over legacy records for the same base video.
    query_scoped_bases = set()
    for _, assets in entries_map.items():
        if not assets.get("query_slug"):
            continue
        vk = assets.get("video")
        if not vk:
            continue
        query_scoped_bases.add(os.path.splitext(os.path.basename(vk))[0])

    for _, assets in entries_map.items():
        video_key = assets['video']
        transcript_key = assets['transcript']
        # Keep only "live" cards: a playable video with transcript data.
        if not video_key or not transcript_key:
            continue
        if not assets.get("query_slug"):
            base_legacy = os.path.splitext(os.path.basename(video_key))[0]
            if base_legacy in query_scoped_bases:
                continue

        thumb_key = assets['thumb']
        meta_key = assets['meta']
        
        # 1. Title
        base_filename = os.path.basename(video_key)
        base_name = os.path.splitext(base_filename)[0]
        real_title = base_name
        if meta_key:
             t = get_metadata_title(client, meta_key)
             if t: real_title = t
             
        # 2. Transcript Info
        keywords = []
        summary = "Generated automatically"
        search_query = None
        if transcript_key:
            s, k, sq = process_transcript(client, transcript_key)
            summary = s
            keywords = k
            search_query = sq
        if not search_query and assets.get('query_slug'):
            q_slug = assets.get('query_slug')
            search_query = query_slug_to_query_text.get(q_slug, q_slug)
            
        query_updated_at = None
        if assets.get('query_slug'):
            q_ts = query_slug_latest_ts.get(assets.get('query_slug'))
            if q_ts is not None:
                query_updated_at = q_ts.isoformat()

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
            "summary": summary,
            "search_query": search_query,
            "query_updated_at": query_updated_at,
        }
        data.append(entry)


    data.sort(key=lambda x: x['title'])
    
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Index generated from {BUCKET_CRES}: {OUTPUT_JSON} with {len(data)} entries.")

if __name__ == "__main__":
    generate_index()
