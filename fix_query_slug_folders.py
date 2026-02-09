#!/usr/bin/env python3
"""
Normalize query folder slugs in MinIO under `queries/<slug>/...`.

Use manifest query text (queries/<slug>/manifest.json -> "query") to recompute slug,
then move all objects to the normalized folder:
  queries/<old>/... -> queries/<new>/...
"""

import json
import re
from io import BytesIO

from minio import Minio
from minio.commonconfig import CopySource

try:
    from pypinyin import lazy_pinyin
except Exception:  # pragma: no cover - optional fallback
    lazy_pinyin = None


def build_client() -> Minio:
    return Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )


def query_slug(query: str) -> str:
    raw = (query or "").strip()
    if not raw:
        return "batch"

    candidate = raw
    if lazy_pinyin is not None:
        try:
            pinyin = "".join(lazy_pinyin(raw))
            if pinyin.strip():
                candidate = pinyin
        except Exception:
            pass

    candidate = candidate.lower()
    candidate = re.sub(r"\s+", "-", candidate)
    candidate = re.sub(r"[^a-z0-9\-_]", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_-")
    return candidate or "batch"


def get_manifest_query(client: Minio, bucket: str, slug: str) -> str:
    key = f"queries/{slug}/manifest.json"
    obj = client.get_object(bucket, key)
    try:
        data = json.loads(obj.read().decode("utf-8"))
    finally:
        obj.close()
        obj.release_conn()
    return str(data.get("query", "")).strip()


def put_manifest_with_slug(client: Minio, bucket: str, slug: str, query: str) -> None:
    key = f"queries/{slug}/manifest.json"
    try:
        obj = client.get_object(bucket, key)
        try:
            data = json.loads(obj.read().decode("utf-8"))
        finally:
            obj.close()
            obj.release_conn()
    except Exception:
        data = {}
    data["query"] = query
    data["slug"] = slug
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    client.put_object(
        bucket,
        key,
        BytesIO(raw),
        length=len(raw),
        content_type="application/json",
    )


def list_slugs(client: Minio, bucket: str) -> list[str]:
    slugs = set()
    for obj in client.list_objects(bucket, prefix="queries/", recursive=True):
        parts = obj.object_name.split("/")
        if len(parts) >= 2 and parts[0] == "queries":
            slugs.add(parts[1])
    return sorted(slugs)


def move_prefix(client: Minio, bucket: str, old_slug: str, new_slug: str) -> tuple[int, int]:
    copied = 0
    deleted = 0
    old_prefix = f"queries/{old_slug}/"
    for obj in client.list_objects(bucket, prefix=old_prefix, recursive=True):
        src = obj.object_name
        rest = src[len(old_prefix):]
        dst = f"queries/{new_slug}/{rest}"
        client.copy_object(bucket, dst, CopySource(bucket, src))
        copied += 1
    for obj in client.list_objects(bucket, prefix=old_prefix, recursive=True):
        client.remove_object(bucket, obj.object_name)
        deleted += 1
    return copied, deleted


def main() -> None:
    bucket = "cres"
    client = build_client()

    moved_slugs = 0
    total_copied = 0
    total_deleted = 0
    skipped = 0

    for slug in list_slugs(client, bucket):
        if slug in {"legacy-orphans"}:
            skipped += 1
            continue
        try:
            query = get_manifest_query(client, bucket, slug)
        except Exception:
            skipped += 1
            continue
        if not query:
            skipped += 1
            continue
        normalized = query_slug(query)
        if normalized == slug:
            continue
        copied, deleted = move_prefix(client, bucket, slug, normalized)
        put_manifest_with_slug(client, bucket, normalized, query)
        moved_slugs += 1
        total_copied += copied
        total_deleted += deleted
        print(f"moved queries/{slug}/ -> queries/{normalized}/ (objects={copied})")

    print(
        f"moved_slugs={moved_slugs} copied={total_copied} deleted={total_deleted} skipped={skipped}"
    )


if __name__ == "__main__":
    main()

