#!/usr/bin/env python3
"""
Safely cleanup legacy MinIO layout objects only when query-scoped counterparts exist.

Legacy prefixes:
  videos/
  thumbnails/
  transcripts/
  process/batch-*/combined-output.json

Query-scoped targets:
  queries/<slug>/videos/<filename>
  queries/<slug>/thumbnails/<filename>
  queries/<slug>/transcripts/<filename>
  queries/<slug>/combined/combined-output.json
"""

import argparse
import re
from collections import defaultdict

from minio import Minio


def build_client() -> Minio:
    return Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )


def collect_query_scoped_index(client: Minio, bucket: str):
    by_folder_filename = defaultdict(set)
    by_query_combined = set()

    for obj in client.list_objects(bucket, prefix="queries/", recursive=True):
        key = obj.object_name
        parts = key.split("/")
        if len(parts) < 4:
            continue
        if parts[0] != "queries":
            continue
        slug = parts[1]
        folder = parts[2]
        filename = parts[-1]

        if folder in {"videos", "thumbnails", "transcripts"}:
            by_folder_filename[(folder, filename)].add(slug)
        if folder == "combined" and filename == "combined-output.json":
            by_query_combined.add(slug)

    return by_folder_filename, by_query_combined


def find_deletable_legacy_keys(client: Minio, bucket: str):
    by_folder_filename, by_query_combined = collect_query_scoped_index(client, bucket)
    deletable = []
    skipped = []

    for obj in client.list_objects(bucket, recursive=True):
        key = obj.object_name
        if key.startswith("queries/"):
            continue

        if key.startswith("videos/"):
            fn = key.split("/", 1)[1]
            if by_folder_filename.get(("videos", fn)):
                deletable.append(key)
            else:
                skipped.append(key)
            continue

        if key.startswith("thumbnails/"):
            fn = key.split("/", 1)[1]
            if by_folder_filename.get(("thumbnails", fn)):
                deletable.append(key)
            else:
                skipped.append(key)
            continue

        if key.startswith("transcripts/"):
            fn = key.split("/", 1)[1]
            if by_folder_filename.get(("transcripts", fn)):
                deletable.append(key)
            else:
                skipped.append(key)
            continue

        m = re.match(r"^process/batch-([^/]+)/combined-output\.json$", key)
        if m:
            slug = m.group(1)
            if slug in by_query_combined:
                deletable.append(key)
            else:
                skipped.append(key)

    return deletable, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Delete keys. Without this flag: dry-run only.")
    args = parser.parse_args()

    client = build_client()
    bucket = "cres"

    deletable, skipped = find_deletable_legacy_keys(client, bucket)
    print(f"deletable={len(deletable)} skipped_unmigrated={len(skipped)}")
    for k in deletable[:100]:
        print(f"DEL {k}")
    if len(deletable) > 100:
        print(f"... and {len(deletable) - 100} more")

    if not args.apply:
        return

    deleted = 0
    for key in deletable:
        try:
            client.remove_object(bucket, key)
            deleted += 1
        except Exception as e:
            print(f"ERR {key}: {e}")
    print(f"deleted={deleted}")


if __name__ == "__main__":
    main()

