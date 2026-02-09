"""
Combined sentence extraction service.

This module extracts evidence sentences for combined keywords while
preserving transcript coverage across videos.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)


class SentenceService:
    """Service for extracting and combining sentences."""

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Split text into sentences using punctuation/newline boundaries."""
        if not text:
            return []
        sentences = re.split(r"[.!?。！？]+[\s\n]*|\n+", text)
        return [s.strip() for s in sentences if s and s.strip()]

    @staticmethod
    def _is_ascii_keyword(keyword: str) -> bool:
        return all(ord(ch) < 128 for ch in (keyword or ""))

    @staticmethod
    def _trim_around_keyword(sentence: str, keyword: str, max_len: int = 220) -> str:
        sentence = (sentence or "").strip()
        if len(sentence) <= max_len:
            return sentence

        idx = sentence.lower().find((keyword or "").lower())
        if idx < 0:
            return sentence[:max_len].strip()

        half = max_len // 2
        start = max(0, idx - half)
        end = min(len(sentence), start + max_len)
        clipped = sentence[start:end].strip()
        if start > 0:
            clipped = "..." + clipped
        if end < len(sentence):
            clipped = clipped + "..."
        return clipped

    @staticmethod
    def find_sentence_with_keyword(sentences: List[str], keyword: str) -> str | None:
        """Find first sentence containing keyword."""
        if not keyword:
            return None

        if SentenceService._is_ascii_keyword(keyword):
            pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        for sentence in sentences:
            if pattern.search(sentence):
                return sentence
        return None

    @staticmethod
    def extract_combined_sentence_from_transcripts(
        transcripts: List[str],
        keywords: List[str],
        max_sentences: int = 5,
    ) -> str:
        """
        Build combined sentence from multiple transcripts with coverage.

        Strategy:
        1) pick at most one evidence sentence per transcript (coverage-first)
        2) backfill with global keyword matches if still under max_sentences
        """
        items = SentenceService.extract_key_sentence_items_from_transcripts(
            transcripts=transcripts,
            keywords=keywords,
            max_sentences=max_sentences,
        )
        evidence_sentences = [item["sentence"] for item in items if item.get("sentence")]

        if not evidence_sentences:
            logger.warning("No evidence sentences found for keywords")
            return ""

        normalized = []
        for sentence in evidence_sentences:
            s = sentence.strip()
            if not s:
                continue
            if not s.endswith((".", "!", "?", "。", "！", "？")):
                s += "."
            normalized.append(s)

        return " ".join(normalized)

    @staticmethod
    def extract_key_sentence_items_from_transcripts(
        transcripts: List[str],
        keywords: List[str],
        max_sentences: int = 5,
    ) -> List[dict]:
        """
        Return structured key sentence items with source transcript index.

        Each item:
        {
            "sentence": str,
            "source_index": int,   # index in transcripts list
            "keyword": str,        # matched keyword, empty when fallback sentence used
        }
        """
        items: List[dict] = []
        seen_sentences = set()

        for idx, transcript in enumerate(transcripts):
            if len(items) >= max_sentences:
                break

            sentences = SentenceService.split_sentences(transcript)
            selected = None
            matched_keyword = ""

            for keyword in keywords:
                selected = SentenceService.find_sentence_with_keyword(sentences, keyword)
                if selected:
                    matched_keyword = keyword
                    selected = SentenceService._trim_around_keyword(selected, keyword)
                    break

            if not selected and sentences:
                selected = SentenceService._trim_around_keyword(sentences[0], "")

            if selected and selected not in seen_sentences:
                items.append(
                    {
                        "sentence": selected,
                        "source_index": idx,
                        "keyword": matched_keyword,
                    }
                )
                seen_sentences.add(selected)

        if len(items) < max_sentences:
            all_indexed_sentences: List[tuple[int, str]] = []
            for idx, transcript in enumerate(transcripts):
                for sentence in SentenceService.split_sentences(transcript):
                    all_indexed_sentences.append((idx, sentence))

            for keyword in keywords:
                if len(items) >= max_sentences:
                    break
                for source_idx, sentence in all_indexed_sentences:
                    probe = SentenceService.find_sentence_with_keyword([sentence], keyword)
                    if not probe:
                        continue
                    probe = SentenceService._trim_around_keyword(probe, keyword)
                    if probe in seen_sentences:
                        continue
                    items.append(
                        {
                            "sentence": probe,
                            "source_index": source_idx,
                            "keyword": keyword,
                        }
                    )
                    seen_sentences.add(probe)
                    break

        return items

    @staticmethod
    def extract_combined_sentence(combined_text: str, keywords: List[str], max_sentences: int = 5) -> str:
        """Backward-compatible wrapper for callers with single combined text."""
        return SentenceService.extract_combined_sentence_from_transcripts(
            transcripts=[combined_text or ""],
            keywords=keywords,
            max_sentences=max_sentences,
        )
