#!/usr/bin/env python3
"""
Migrate legacy MinIO layout to query-scoped layout without deleting old objects.

Legacy:
  videos/<file>
  transcripts/<file>.json
  thumbnails/<file>
  process/batch-<slug>/combined-output.json

New:
  queries/<slug>/videos/<file>
  queries/<slug>/transcripts/<file>.json
  queries/<slug>/thumbnails/<file>
  queries/<slug>/combined/combined-output.json
  queries/<slug>/manifest.json
"""

import json
import os
import re
import urllib.parse
from io import BytesIO
from pathlib import Path
from typing import Dict, List

from minio import Minio
from minio.error import S3Error


BUCKET = os.getenv("MINIO_BUCKET", "cres")
ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
ACCESS = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET = os.getenv("MINIO_SECRET_KEY", "minioadmin")


def slugify(query: str) -> str:
    q = (query or "").strip().lower()
    q = re.sub(r"\s+", "-", q)
    q = re.sub(r"[^a-z0-9\-_]", "_", q)
    return q or "batch"


def key_from_url(url: str, bucket: str) -> str:
    if not url:
        return ""
    if not url.startswith("http://") and not url.startswith("https://"):
        return url.lstrip("/")
    p = urllib.parse.urlparse(url)
    path = p.path.lstrip("/")
    prefix = f"{bucket}/"
    if path.startswith(prefix):
        return urllib.parse.unquote(path[len(prefix):])
    return urllib.parse.unquote(path)


def object_exists(client: Minio, key: str) -> bool:
    try:
        client.stat_object(BUCKET, key)
        return True
    except Exception:
        return False


def copy_object(client: Minio, src_key: str, dst_key: str) -> bool:
    if not src_key or not dst_key:
        return False
    if object_exists(client, dst_key):
        return False
    try:
        obj = client.get_object(BUCKET, src_key)
        try:
            raw = obj.read()
        finally:
            obj.close()
            obj.release_conn()
        content_type = "application/octet-stream"
        if dst_key.endswith(".json"):
            content_type = "application/json"
        elif dst_key.endswith((".jpg", ".jpeg", ".png", ".webp")):
            content_type = "image/*"
        elif dst_key.endswith((".mp4", ".webm", ".mkv", ".avi", ".mov")):
            content_type = "video/*"
        client.put_object(BUCKET, dst_key, BytesIO(raw), len(raw), content_type=content_type)
        return True
    except S3Error:
        return False
    except Exception:
        return False


def load_index() -> List[dict]:
    path = Path("web/src/data.json")
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    client = Minio(ENDPOINT, access_key=ACCESS, secret_key=SECRET, secure=False)
    records = load_index()
    grouped: Dict[str, List[dict]] = {}
    for r in records:
        q = r.get("search_query")
        if not q:
            continue
        grouped.setdefault(q, []).append(r)

    copied = 0
    manifests = 0
    for query, rows in grouped.items():
        slug = slugify(query)
        prefix = f"queries/{slug}"
        manifest = {
            "query": query,
            "slug": slug,
            "videos": [],
            "combined": {},
        }

        for r in rows:
            video_key = key_from_url(r.get("video_path", ""), BUCKET)
            trans_key = key_from_url(r.get("json_path", ""), BUCKET)
            thumb_key = key_from_url(r.get("thumb_path", ""), BUCKET) if r.get("thumb_path") else ""

            if video_key:
                dst_video = f"{prefix}/videos/{os.path.basename(video_key)}"
                if copy_object(client, video_key, dst_video):
                    copied += 1
            else:
                dst_video = ""

            if trans_key:
                dst_trans = f"{prefix}/transcripts/{os.path.basename(trans_key)}"
                if copy_object(client, trans_key, dst_trans):
                    copied += 1
            else:
                dst_trans = ""

            if thumb_key:
                dst_thumb = f"{prefix}/thumbnails/{os.path.basename(thumb_key)}"
                if copy_object(client, thumb_key, dst_thumb):
                    copied += 1
            else:
                dst_thumb = ""

            manifest["videos"].append(
                {
                    "object_key": dst_video,
                    "transcript_key": dst_trans,
                    "thumbnail_key": dst_thumb,
                    "search_query": query,
                    "status": "migrated",
                }
            )

        legacy_combined = f"process/batch-{slug}/combined-output.json"
        new_combined = f"{prefix}/combined/combined-output.json"
        if copy_object(client, legacy_combined, new_combined) or object_exists(client, new_combined):
            manifest["combined"]["combined_output_key"] = new_combined
            manifest["combined"]["status"] = "migrated"

        raw = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        client.put_object(BUCKET, f"{prefix}/manifest.json", BytesIO(raw), len(raw), content_type="application/json")
        manifests += 1

    print(f"migrated_manifests={manifests} copied_objects={copied}")


if __name__ == "__main__":
    main()

