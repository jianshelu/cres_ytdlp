#!/usr/bin/env python3
"""
Rebuild combined transcription artifacts for existing queries WITHOUT running
search/download/transcription workflows, and regenerate a persistent
combined-video.mp4 using key-sentence segments.

Examples:
  python scripts/rebuild_combined_output.py --query "Anti gravity"
  python scripts/rebuild_combined_output.py --all
  python scripts/rebuild_combined_output.py --query "Anti gravity" --refresh-index
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.parse
from typing import Any

from minio import Minio

PROJECT_ROOT: pathlib.Path | None = None


def _bootstrap_project_path() -> None:
    """Ensure repo root (containing src/backend/activities.py) is importable."""
    global PROJECT_ROOT
    script_dir = pathlib.Path(__file__).resolve().parent
    cwd = pathlib.Path.cwd().resolve()

    candidates: list[pathlib.Path] = []
    candidates.extend([script_dir, *script_dir.parents])
    candidates.extend([cwd, *cwd.parents])
    candidates.extend([cwd / "cres_ytdlp", script_dir.parent / "cres_ytdlp"])

    seen: set[str] = set()
    for c in candidates:
        c_str = str(c)
        if c_str in seen:
            continue
        seen.add(c_str)
        if (c / "src" / "backend" / "activities.py").exists():
            PROJECT_ROOT = c
            if c_str not in sys.path:
                sys.path.insert(0, c_str)
            return


_bootstrap_project_path()

from src.backend.activities import build_batch_combined_output, refresh_index

try:
    from pypinyin import lazy_pinyin
except Exception:
    lazy_pinyin = None


def _query_slug(query: str) -> str:
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


def _get_client() -> Minio:
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    secure = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def _read_json_object(client: Minio, bucket: str, key: str) -> dict[str, Any]:
    obj = client.get_object(bucket, key)
    try:
        return json.loads(obj.read().decode("utf-8"))
    finally:
        obj.close()
        obj.release_conn()


def _write_json_object(client: Minio, bucket: str, key: str, payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    client.put_object(
        bucket,
        key,
        data=io.BytesIO(raw),
        length=len(raw),
        content_type="application/json",
    )


def _load_manifest(client: Minio, bucket: str, query: str) -> dict[str, Any]:
    key = f"queries/{_query_slug(query)}/manifest.json"
    return _read_json_object(client, bucket, key)


def _save_manifest(client: Minio, bucket: str, query: str, manifest: dict[str, Any]) -> None:
    key = f"queries/{_query_slug(query)}/manifest.json"
    _write_json_object(client, bucket, key, manifest)


def _child_results_from_manifest(manifest: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    videos = manifest.get("videos", [])
    if not isinstance(videos, list):
        return out

    for item in videos:
        if not isinstance(item, dict):
            continue
        object_key = item.get("object_key")
        if not object_key or not isinstance(object_key, str):
            continue
        out.append({"filepath": object_key})
    return out


def _normalize_compact(value: str) -> str:
    return re.sub(r"[^\u4e00-\u9fff\w]", "", (value or "").lower())


def _find_best_segment(sentence: str, segments: list[dict]) -> tuple[float, float]:
    target = _normalize_compact(sentence)
    if not target:
        return (0.0, 12.0)

    best = None
    best_score = 0.0
    for seg in segments:
        text = _normalize_compact(str(seg.get("text", "")))
        if not text:
            continue
        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start + 0.5))
        except Exception:
            continue
        if text in target or target in text:
            return (max(0.0, start), max(start + 0.5, end))
        prefix = target[: min(20, len(target))]
        if prefix and prefix in text:
            score = len(prefix) / max(len(text), 1)
            if score > best_score:
                best_score = score
                best = (start, end)
    if best:
        return (max(0.0, best[0]), max(best[0] + 0.5, best[1]))
    return (0.0, 12.0)


def _probe_duration(video_path: pathlib.Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
    try:
        return float(out)
    except Exception:
        return 0.0


def _clip_window(start: float, end: float, duration: float) -> tuple[float, float]:
    raw_start = max(0.0, start)
    raw_end = max(raw_start + 0.5, end)
    clip_start = max(0.0, raw_start - 1.5)
    clip_end = max(clip_start + 8.0, raw_end + 3.5)
    clip_end = min(clip_end, clip_start + 14.0)
    if duration > 0:
        clip_end = min(clip_end, duration)
        if clip_end <= clip_start + 0.5:
            clip_start = max(0.0, duration - 8.0)
            clip_end = duration
    return (clip_start, max(clip_start + 0.5, clip_end))


def _build_combined_video_for_query(client: Minio, bucket: str, query: str) -> dict[str, Any]:
    slug = _query_slug(query)
    combined_key = f"queries/{slug}/combined/combined-output.json"
    payload = _read_json_object(client, bucket, combined_key)
    key_sentences = payload.get("key_sentences", []) or []
    transcripts = payload.get("transcripts", []) or []

    if not key_sentences:
        return {"status": "skip", "reason": "no-key-sentences"}

    transcript_by_video = {}
    for item in transcripts:
        if not isinstance(item, dict):
            continue
        video_object = str(item.get("video_object", "")).strip()
        if video_object:
            transcript_by_video[video_object] = item

    with tempfile.TemporaryDirectory(prefix=f"recombine-{slug}-") as td:
        tmp = pathlib.Path(td)
        source_cache: dict[str, pathlib.Path] = {}
        clip_paths: list[pathlib.Path] = []
        clip_meta: list[dict[str, Any]] = []

        for idx, ks in enumerate(key_sentences[:5]):
            if not isinstance(ks, dict):
                continue
            source_video_key = str(ks.get("source_video_object", "")).strip()
            sentence = str(ks.get("sentence", "")).strip()
            if not source_video_key:
                src_i = int(ks.get("source_index", -1))
                if 0 <= src_i < len(transcripts):
                    source_video_key = str(transcripts[src_i].get("video_object", "")).strip()
            if not source_video_key:
                continue

            local_video = source_cache.get(source_video_key)
            if not local_video:
                base = pathlib.Path(source_video_key).name
                local_video = tmp / f"src_{len(source_cache)}_{base}"
                client.fget_object(bucket, source_video_key, str(local_video))
                source_cache[source_video_key] = local_video

            transcript_key = ""
            t_item = transcript_by_video.get(source_video_key, {})
            if isinstance(t_item, dict):
                transcript_key = str(t_item.get("transcript_key", "")).strip()

            seg_start = 0.0
            seg_end = 12.0
            if transcript_key:
                t_payload = _read_json_object(client, bucket, transcript_key)
                segments = t_payload.get("segments", []) or []
                if isinstance(segments, list):
                    seg_start, seg_end = _find_best_segment(sentence, segments)

            duration = _probe_duration(local_video)
            clip_start, clip_end = _clip_window(seg_start, seg_end, duration)

            clip_path = tmp / f"clip_{idx:02d}.mp4"
            cmd_clip = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{clip_start:.3f}",
                "-to",
                f"{clip_end:.3f}",
                "-i",
                str(local_video),
                "-vf",
                "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,fps=30",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "24",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                str(clip_path),
            ]
            subprocess.run(cmd_clip, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            clip_paths.append(clip_path)
            clip_meta.append(
                {
                    "source_video_object": source_video_key,
                    "sentence": sentence,
                    "clip_start": round(clip_start, 3),
                    "clip_end": round(clip_end, 3),
                    "clip_duration": round(max(0.0, clip_end - clip_start), 3),
                }
            )

        if not clip_paths:
            return {"status": "skip", "reason": "no-clips-generated"}

        concat_txt = tmp / "concat.txt"
        concat_txt.write_text(
            "\n".join([f"file '{p.as_posix()}'" for p in clip_paths]),
            encoding="utf-8",
        )
        out_video = tmp / "combined-video.mp4"
        cmd_concat = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
            "-c",
            "copy",
            str(out_video),
        ]
        try:
            subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            cmd_concat_fallback = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_txt),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "24",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                str(out_video),
            ]
            subprocess.run(cmd_concat_fallback, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        combined_video_key = f"queries/{slug}/combined/combined-video.mp4"
        client.fput_object(bucket, combined_video_key, str(out_video), content_type="video/mp4")
        encoded_key = urllib.parse.quote(combined_video_key)
        minio_public_base = os.getenv("MINIO_PUBLIC_BASE_URL", "").strip().rstrip("/")
        if minio_public_base:
            combined_video_url = f"{minio_public_base}/{bucket}/{encoded_key}"
        else:
            scheme = "https" if os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"} else "http"
            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            combined_video_url = f"{scheme}://{endpoint}/{bucket}/{encoded_key}"

        rebuilt_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        payload["combined_video_key"] = combined_video_key
        payload["combined_video_url"] = combined_video_url
        payload["combined_video_clip_count"] = len(clip_paths)
        payload["combined_video_clips"] = clip_meta
        payload["recombined_sentence"] = True
        payload["combined_sentence_version"] = "recombined-v2"
        payload["combined_rebuilt_at_utc"] = rebuilt_at
        _write_json_object(client, bucket, combined_key, payload)

        return {
            "status": "ok",
            "combined_video_key": combined_video_key,
            "combined_video_url": combined_video_url,
            "clip_count": len(clip_paths),
            "recombined_sentence": True,
            "combined_sentence_version": "recombined-v2",
            "combined_rebuilt_at_utc": rebuilt_at,
        }


def _list_queries_from_manifests(client: Minio, bucket: str) -> list[str]:
    queries = []
    seen = set()
    for obj in client.list_objects(bucket, prefix="queries/", recursive=True):
        key = obj.object_name
        if not key.endswith("/manifest.json"):
            continue
        try:
            payload = _read_json_object(client, bucket, key)
        except Exception:
            continue
        q = str(payload.get("query", "")).strip()
        if not q:
            m = re.match(r"^queries/([^/]+)/manifest\.json$", key)
            q = m.group(1) if m else ""
        if q and q not in seen:
            seen.add(q)
            queries.append(q)
    return queries


async def _run_one_query(client: Minio, bucket: str, query: str, build_video: bool) -> dict[str, Any]:
    manifest = _load_manifest(client, bucket, query)
    child_results = _child_results_from_manifest(manifest)
    if not child_results:
        return {"query": query, "status": "skip", "reason": "no-videos-in-manifest"}

    combined_result = await build_batch_combined_output((query, child_results))
    video_result: dict[str, Any] = {"status": "skip", "reason": "video-build-disabled"}
    if build_video:
        video_result = _build_combined_video_for_query(client, bucket, query)

    # Mark manifest combined section.
    try:
        manifest = _load_manifest(client, bucket, query)
    except Exception:
        manifest = {"query": query}
    combined = manifest.get("combined", {})
    if not isinstance(combined, dict):
        combined = {}
    if isinstance(video_result, dict) and video_result.get("status") == "ok":
        combined["combined_video_key"] = video_result.get("combined_video_key", "")
        combined["combined_video_url"] = video_result.get("combined_video_url", "")
        combined["combined_video_clip_count"] = int(video_result.get("clip_count", 0) or 0)
        combined["recombined_sentence"] = True
        combined["combined_sentence_version"] = "recombined-v2"
        combined["combined_rebuilt_at_utc"] = video_result.get("combined_rebuilt_at_utc", "")
    manifest["combined"] = combined
    _save_manifest(client, bucket, query, manifest)

    return {
        "query": query,
        "combined_output": combined_result,
        "combined_video": video_result,
    }


async def _run(queries: list[str], refresh: bool, build_video: bool) -> int:
    client = _get_client()
    bucket = "cres"
    results = []
    failures = 0
    for q in queries:
        try:
            result = await _run_one_query(client, bucket, q, build_video=build_video)
            results.append(result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            failures += 1
            err = {"query": q, "status": "error", "error": str(e)}
            results.append(err)
            print(json.dumps(err, ensure_ascii=False, indent=2))

    if refresh:
        idx = refresh_index()
        print("\n[Index Refresh]")
        print(idx)

    print("\n[Summary]")
    print(json.dumps({"total": len(queries), "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild combined outputs and regenerate combined video for existing query data."
    )
    parser.add_argument("--query", help="Single search query to rebuild.")
    parser.add_argument("--all", action="store_true", help="Rebuild all queries found in MinIO manifests.")
    parser.add_argument("--refresh-index", action="store_true", help="Run index refresh after rebuild.")
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Only rebuild combined text/keywords/sentences, skip combined-video generation.",
    )
    args = parser.parse_args()

    if not args.query and not args.all:
        print("[ERROR] Provide --query or --all")
        return 2

    if PROJECT_ROOT is not None:
        os.chdir(PROJECT_ROOT)

    client = _get_client()
    queries: list[str]
    if args.all:
        queries = _list_queries_from_manifests(client, "cres")
    else:
        queries = [str(args.query).strip()]
    queries = [q for q in queries if q]
    if not queries:
        print("[WARN] No queries found to rebuild.")
        return 0

    try:
        return asyncio.run(_run(queries, refresh=args.refresh_index, build_video=not args.skip_video))
    except Exception as e:
        print(f"[ERROR] Failed to rebuild: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
