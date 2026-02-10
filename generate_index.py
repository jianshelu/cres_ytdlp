import io
import json
import os
import re
import urllib.parse

from minio import Minio

OUTPUT_JSON = "web/src/data.json"


def _bool_env(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _load_env_file_if_present(path: str = ".env") -> None:
    # Keep this dependency-free so the script works in minimal environments.
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def _resolve_minio_settings():
    endpoint_raw = os.getenv("MINIO_ENDPOINT", "localhost:9000").strip()
    secure_env_set = "MINIO_SECURE" in os.environ

    if endpoint_raw.startswith("http://"):
        endpoint = endpoint_raw[len("http://") :]
        secure = _bool_env("MINIO_SECURE", False) if secure_env_set else False
    elif endpoint_raw.startswith("https://"):
        endpoint = endpoint_raw[len("https://") :]
        secure = _bool_env("MINIO_SECURE", True) if secure_env_set else True
    else:
        endpoint = endpoint_raw
        secure = _bool_env("MINIO_SECURE", False)

    access_key = os.getenv("MINIO_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"))
    secret_key = os.getenv("MINIO_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"))
    bucket = os.getenv("MINIO_BUCKET", "cres")

    public_base = os.getenv("MINIO_PUBLIC_BASE_URL", "").strip()
    if public_base:
        url_base = public_base.rstrip("/")
    else:
        url_base = f"{'https' if secure else 'http'}://{endpoint}"

    return endpoint, access_key, secret_key, secure, bucket, url_base


def get_minio_client():
    endpoint, access_key, secret_key, secure, _bucket, _url_base = _resolve_minio_settings()
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def get_metadata_title(client, bucket: str, object_key: str):
    try:
        response = client.get_object(bucket, object_key)
        meta = json.load(response)
        response.close()
        response.release_conn()

        if isinstance(meta, dict) and "title" in meta:
            return meta["title"]
    except Exception:
        pass
    return None


def process_transcript(client, bucket: str, object_key: str):
    """
    Reads transcript, scores keywords, updates if needed, returns (summary, keywords, search_query).
    """
    summary = "Generated automatically"
    keywords = []
    search_query = None

    try:
        response = client.get_object(bucket, object_key)
        data = json.load(response)
        response.close()
        response.release_conn()

        if "summary" in data:
            summary = data["summary"]

        if "search_query" in data:
            search_query = data["search_query"]

        if "keywords" in data:
            keywords_list = []
            text_lower = data.get("text", "").lower()
            segments = data.get("segments", [])
            raw_keywords = data["keywords"]
            dirty = False

            for k in raw_keywords:
                word_str = ""
                if isinstance(k, str):
                    word_str = k
                    dirty = True
                elif isinstance(k, dict) and "word" in k:
                    word_str = k["word"]
                else:
                    continue

                clean_k = word_str.strip()
                if not clean_k:
                    continue

                count = text_lower.count(clean_k.lower())

                if count >= 20:
                    score = 5
                elif count >= 10:
                    score = 4
                elif count >= 5:
                    score = 3
                elif count >= 3:
                    score = 2
                else:
                    score = 1

                start_time = 0
                for seg in segments:
                    pattern = re.compile(rf"\\b{re.escape(clean_k)}\\b", re.IGNORECASE)
                    if pattern.search(seg.get("text", "")):
                        start_time = seg.get("start", 0)
                        break

                keywords_list.append({"word": clean_k, "count": count, "score": score, "start_time": start_time})

            keywords_list.sort(key=lambda x: (x["score"], x["count"]), reverse=True)
            keywords_list = keywords_list[:5]

            if dirty:
                data["keywords"] = keywords_list
                new_content = json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8")
                client.put_object(
                    bucket,
                    object_key,
                    io.BytesIO(new_content),
                    len(new_content),
                    content_type="application/json",
                )
                keywords = keywords_list
            else:
                keywords = keywords_list

    except Exception as e:
        print(f"Error processing transcript {object_key}: {e}")

    return summary, keywords, search_query


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in (text or ""))


def _is_likely_garbled_query(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return False
    # Common mojibake signals when UTF-8 Chinese was decoded using a wrong code page.
    if "�" in s:
        return True
    if any("\u0400" <= ch <= "\u04ff" for ch in s):  # Cyrillic range
        return True
    # Non-empty but not CJK/ASCII-ish often indicates encoding damage in this project context.
    if not _contains_cjk(s):
        non_ascii = sum(1 for ch in s if ord(ch) > 127)
        if non_ascii > 0 and re.search(r"[A-Za-z0-9]", s) is None:
            return True
    return False


def generate_index():
    _load_env_file_if_present()
    _endpoint, _ak, _sk, _secure, bucket, url_base = _resolve_minio_settings()
    client = get_minio_client()

    if not client.bucket_exists(bucket):
        print(f"Bucket {bucket} does not exist.")
        return

    objects = client.list_objects(bucket, recursive=True)

    entries_map = {}
    query_slug_latest_ts = {}
    query_slug_to_query_text = {}

    video_extensions = (".mp4", ".webm", ".mkv", ".avi", ".mov")
    image_extensions = (".jpg", ".webp", ".png", ".jpeg")

    for obj in objects:
        key = obj.object_name
        parts = key.split("/")
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
                    obj_manifest = client.get_object(bucket, key)
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

        if filename.endswith(".info.json"):
            base = filename[:-10]
        else:
            base = os.path.splitext(filename)[0]

        entry_id = f"{query_slug or '_legacy'}::{base}"
        if entry_id not in entries_map:
            entries_map[entry_id] = {
                "video": None,
                "thumb": None,
                "meta": None,
                "transcript": None,
                "query_slug": query_slug,
            }

        if folder == "videos":
            if filename.endswith(".info.json"):
                entries_map[entry_id]["meta"] = key
            elif filename.lower().endswith(video_extensions):
                entries_map[entry_id]["video"] = key
        elif folder == "thumbnails":
            if filename.lower().endswith(image_extensions):
                entries_map[entry_id]["thumb"] = key
        elif folder == "transcripts":
            if filename.endswith(".json"):
                entries_map[entry_id]["transcript"] = key

    data = []
    query_scoped_bases = set()
    for _eid, assets in entries_map.items():
        if not assets.get("query_slug"):
            continue
        vk = assets.get("video")
        if not vk:
            continue
        query_scoped_bases.add(os.path.splitext(os.path.basename(vk))[0])

    for _eid, assets in entries_map.items():
        video_key = assets["video"]
        transcript_key = assets["transcript"]
        if not video_key or not transcript_key:
            continue
        if not assets.get("query_slug"):
            base_legacy = os.path.splitext(os.path.basename(video_key))[0]
            if base_legacy in query_scoped_bases:
                continue

        thumb_key = assets["thumb"]
        meta_key = assets["meta"]

        base_filename = os.path.basename(video_key)
        base_name = os.path.splitext(base_filename)[0]
        real_title = base_name
        if meta_key:
            t = get_metadata_title(client, bucket, meta_key)
            if t:
                real_title = t

        keywords = []
        summary = "Generated automatically"
        search_query = None
        if transcript_key:
            s, k, sq = process_transcript(client, bucket, transcript_key)
            summary = s
            keywords = k
            search_query = sq
        q_slug = assets.get("query_slug")
        if q_slug and (not search_query or _is_likely_garbled_query(search_query)):
            search_query = query_slug_to_query_text.get(q_slug, q_slug)

        query_updated_at = None
        if assets.get("query_slug"):
            q_ts = query_slug_latest_ts.get(assets.get("query_slug"))
            if q_ts is not None:
                query_updated_at = q_ts.isoformat()

        enc_video = urllib.parse.quote(video_key) if video_key else None
        enc_thumb = urllib.parse.quote(thumb_key) if thumb_key else None
        enc_trans = urllib.parse.quote(transcript_key) if transcript_key else None

        entry = {
            "title": real_title,
            "video_path": f"{url_base}/{bucket}/{enc_video}",
            "thumb_path": f"{url_base}/{bucket}/{enc_thumb}" if enc_thumb else None,
            "json_path": f"{url_base}/{bucket}/{enc_trans}" if enc_trans else None,
            "keywords": keywords,
            "summary": summary,
            "search_query": search_query,
            "query_updated_at": query_updated_at,
        }
        data.append(entry)

    data.sort(key=lambda x: x["title"])

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Index generated from {bucket}: {OUTPUT_JSON} with {len(data)} entries.")


if __name__ == "__main__":
    generate_index()
