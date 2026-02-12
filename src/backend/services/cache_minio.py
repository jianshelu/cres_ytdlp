"""
MinIO-backed cache for transcriptions aggregate responses.
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


def _normalize_query(query: str) -> str:
    norm = re.sub(r"\s+", "-", query.strip().lower())
    norm = re.sub(r"[^a-z0-9\-_]", "_", norm)
    return norm or "empty"


def build_source_hash(videos: List[dict], limit: int) -> str:
    """Hash inputs that should invalidate cache when they change."""
    source_items = [
        {
            "video_path": v.get("video_path"),
            "json_path": v.get("json_path"),
            "title": v.get("title"),
            "search_query": v.get("search_query"),
        }
        for v in videos[:limit]
    ]
    raw = json.dumps({"limit": limit, "videos": source_items}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class MinioTranscriptionsCache:
    def __init__(self) -> None:
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}

        self.bucket = os.getenv("MINIO_CACHE_BUCKET", "cres")
        self.prefix = os.getenv("MINIO_CACHE_PREFIX", "cache/transcriptions")

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def _build_key(self, query: str, limit: int, source_hash: str) -> str:
        norm_q = _normalize_query(query)
        return f"{self.prefix}/v2/{norm_q}/limit-{limit}/{source_hash}.json"

    def get(self, query: str, limit: int, source_hash: str) -> Optional[Dict[str, Any]]:
        key = self._build_key(query, limit, source_hash)
        try:
            data = self.client.get_object(self.bucket, key)
            try:
                payload = data.read()
            finally:
                data.close()
                data.release_conn()
            parsed = json.loads(payload.decode("utf-8"))
            logger.info(f"Transcriptions cache hit: {key}")
            return parsed
        except S3Error as e:
            # Expected when object does not exist.
            if getattr(e, "code", "") in {"NoSuchKey", "NoSuchObject"}:
                logger.info(f"Transcriptions cache miss: {key}")
                return None
            logger.warning(f"Transcriptions cache read error for {key}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Transcriptions cache parse/read error for {key}: {e}")
            return None

    def set(
        self,
        query: str,
        limit: int,
        source_hash: str,
        response_payload: Dict[str, Any],
        combined_transcription: str,
    ) -> None:
        key = self._build_key(query, limit, source_hash)
        cache_payload = {
            "cached_at_utc": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "limit": limit,
            "source_hash": source_hash,
            "combinedTranscription": combined_transcription,
            "combinedKeywordTags": response_payload.get("combined", {}).get("keywords", []),
            "combinedSentence": response_payload.get("combined", {}).get("sentence", ""),
            "response": response_payload,
        }
        raw = json.dumps(cache_payload, ensure_ascii=False).encode("utf-8")
        stream = BytesIO(raw)
        try:
            self._ensure_bucket()
            self.client.put_object(
                self.bucket,
                key,
                stream,
                length=len(raw),
                content_type="application/json",
            )
            logger.info(f"Transcriptions cache stored: {key}")
        except Exception as e:
            logger.warning(f"Transcriptions cache write failed for {key}: {e}")
