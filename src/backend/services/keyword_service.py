"""
Keyword extraction service with LLM integration and coverage compensation.

This module implements the core keyword extraction algorithm:
- LLM provides semantic relevance scores
- Program calculates occurrence counts from actual text
- Coverage compensation ensures each transcript is represented
- Sorting: Score DESC → Count DESC → term ASC
"""

import re
import logging
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
from pydantic import BaseModel

from .llm_llamacpp import LlamaCppClient, LLMKeywordResponse

logger = logging.getLogger(__name__)

# Algorithm parameters
TOPK = 5  # Number of combined keywords
CORE_KEEP = 2  # Protect top N core keywords from replacement
MAX_REPLACE = 3  # Maximum replacement iterations
COL_K = 5  # Keywords per column/video

class Keyword(BaseModel):
    """Keyword with score and count."""
    term: str
    score: float
    count: int

class KeywordExtractionService:
    """Service for extracting and processing keywords."""
    
    def __init__(self, llm_client: LlamaCppClient):
        """
        Initialize keyword extraction service.
        
        Args:
            llm_client: LlamaCppClient instance for LLM calls
        """
        self.llm = llm_client

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text or ""))

    @staticmethod
    def _is_cjk_query(query: str) -> bool:
        return KeywordExtractionService._contains_cjk(query or "")

    @staticmethod
    def _is_term_compatible_with_query_language(term: str, query_is_cjk: bool) -> bool:
        if not term:
            return False
        term_has_cjk = KeywordExtractionService._contains_cjk(term)
        if query_is_cjk:
            # Chinese query should return Chinese terms.
            return term_has_cjk
        # Non-Chinese query can keep both latin/entity words and mixed tokens.
        return True

    @staticmethod
    def is_low_quality_term(term: str) -> bool:
        t = (term or "").strip().lower().replace("’", "'").replace("`", "'")
        if not t:
            return True
        t_no_apo = t.replace("'", "")

        generic_en = {
            "because", "users", "user", "people", "person", "thing", "things", "today",
            "now", "then", "also", "just", "really", "very", "some", "many", "much",
            "more", "most", "less", "least", "good", "bad", "better", "best", "worse",
            "new", "old", "big", "small", "high", "low", "use", "used", "using", "make",
            "made", "get", "got", "take", "taken", "look", "looks", "looking", "say",
            "said", "go", "goes", "went", "come", "came", "know", "known", "need", "needs",
            "want", "wants", "think", "thinks", "its", "it's", "this", "that", "these",
            "those", "there", "here", "their", "them", "they", "we", "our", "you", "your",
            "theyre", "were", "youre", "im", "ive", "dont", "cant", "wont", "thats", "theres",
        }
        generic_cn = {
            "这个", "那个", "这些", "那些", "我们", "你们", "他们", "然后", "就是", "可以", "没有",
            "因为", "所以", "现在", "已经", "还是", "但是", "一个", "一些", "很多", "比较", "非常",
            "东西", "内容", "问题", "情况", "时候", "地方", "方面",
        }

        if t in generic_en or t_no_apo in generic_en or t in generic_cn:
            return True

        has_cjk = KeywordExtractionService._contains_cjk(t)
        if has_cjk:
            return len(t) < 2

        # For latin terms, keep only meaningful words/phrases.
        short_allow = {"ai", "llm", "gpu", "cpu", "api", "sdk"}
        if t in short_allow:
            return False
        if len(t) < 3:
            return True
        if re.fullmatch(r"\d+([.-]\d+)?", t):
            return True
        if not re.search(r"[a-z]", t):
            return True
        return False

    @staticmethod
    def _fallback_keywords_from_text(text: str, k: int = 30) -> List[Keyword]:
        """
        Deterministic fallback when LLM output is unavailable or unusable.
        Uses simple token frequency with lightweight stop-word filtering.
        """
        if KeywordExtractionService._contains_cjk(text):
            stop_cn = {
                "我们", "你们", "他们", "这个", "那个", "以及", "因为", "所以", "可以", "一个",
                "没有", "如果", "就是", "然后", "什么", "怎么", "现在", "已经", "还是", "但是",
            }
            tokens_cn = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
            counts_cn: Dict[str, int] = defaultdict(int)
            for t in tokens_cn:
                if t in stop_cn:
                    continue
                counts_cn[t] += 1
            if counts_cn:
                ranked_cn = sorted(counts_cn.items(), key=lambda x: (-x[1], x[0]))[:k]
                max_count_cn = ranked_cn[0][1] if ranked_cn else 1
                return [
                    Keyword(term=term, count=count, score=min(1.0, count / max_count_cn))
                    for term, count in ranked_cn
                ]

        stop_words = {
            "the", "and", "for", "that", "this", "with", "you", "your", "are", "was",
            "have", "has", "had", "from", "they", "their", "about", "there", "what",
            "when", "where", "which", "will", "would", "could", "should", "into",
            "just", "like", "more", "than", "then", "over", "very", "some", "such",
            "been", "being", "also", "but", "not", "its", "our", "out", "all", "can",
            "get", "got", "one", "two", "three", "how", "why", "who", "whom", "whose",
            "video", "today", "people", "thing", "things", "make", "made", "using",
        }

        tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text.lower())
        counts: Dict[str, int] = defaultdict(int)
        for t in tokens:
            if t in stop_words:
                continue
            counts[t] += 1

        if not counts:
            return []

        ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:k]
        max_count = ranked[0][1] if ranked else 1

        return [
            Keyword(term=term, count=count, score=min(1.0, count / max_count))
            for term, count in ranked
        ]
        
    @staticmethod
    def normalize_term(term: str) -> str:
        """
        Normalize keyword term (lowercase, remove punctuation).
        
        Args:
            term: Raw keyword term
            
        Returns:
            Normalized term
        """
        # Lowercase and remove punctuation
        term = term.lower().strip().replace("’", "'").replace("`", "'")
        term = re.sub(r"\b([a-z0-9]+)'s\b", r"\1", term)
        term = re.sub(r'[^\w\s-]', '', term)
        term = re.sub(r'\s+', ' ', term)
        return term
    
    @staticmethod
    def count_occurrences(term: str, text: str) -> int:
        """
        Count word-boundary occurrences of term in text (case-insensitive).
        
        Args:
            term: Search term
            text: Text to search in
            
        Returns:
            Occurrence count
        """
        if KeywordExtractionService._contains_cjk(term):
            # CJK text does not use whitespace boundaries like latin words.
            pattern = re.compile(re.escape(term), re.IGNORECASE)
        else:
            pattern = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
        return len(pattern.findall(text))

    @staticmethod
    def filter_keywords_by_query_language(keywords: List[Keyword], query: str) -> List[Keyword]:
        """Keep keywords consistent with query language (Chinese query => Chinese keywords)."""
        query_is_cjk = KeywordExtractionService._is_cjk_query(query)
        out = []
        for kw in keywords:
            if KeywordExtractionService._is_term_compatible_with_query_language(kw.term, query_is_cjk):
                out.append(kw)
        return out

    @staticmethod
    def filter_low_quality_keywords(keywords: List[Keyword]) -> List[Keyword]:
        out = []
        seen = set()
        for kw in keywords:
            term = (kw.term or "").strip()
            if not term:
                continue
            if KeywordExtractionService.is_low_quality_term(term):
                continue
            norm = term.lower()
            if norm in seen:
                continue
            seen.add(norm)
            out.append(kw)
        return out
    
    @staticmethod
    def merge_keywords(llm_response: LLMKeywordResponse, text: str) -> List[Keyword]:
        """
        Merge LLM keywords with occurrence counts and deduplicate.
        
        Args:
            llm_response: LLM extraction response
            text: Source text for counting occurrences
            
        Returns:
            List of Keywords with counts, sorted by score DESC, count DESC
        """
        term_map: Dict[str, Keyword] = {}
        
        for candidate in llm_response.keywords:
            normalized = KeywordExtractionService.normalize_term(candidate.term)
            if not normalized:
                continue
            if KeywordExtractionService.is_low_quality_term(normalized):
                continue
                
            count = KeywordExtractionService.count_occurrences(normalized, text)
            
            # Skip terms not found in text (LLM hallucination)
            if count == 0:
                continue
            
            # Merge duplicates (take max score)
            if normalized in term_map:
                term_map[normalized].score = max(term_map[normalized].score, candidate.score)
            else:
                term_map[normalized] = Keyword(
                    term=normalized,
                    score=candidate.score,
                    count=count
                )
        
        # Sort by score DESC, count DESC, term ASC
        sorted_keywords = sorted(
            term_map.values(),
            key=lambda k: (-k.score, -k.count, k.term)
        )
        
        return sorted_keywords
    
    async def extract_single_keywords(
        self,
        query: str,
        transcript: str,
        k: int = 30
    ) -> List[Keyword]:
        """
        Extract keywords from a single transcript.
        
        Args:
            query: Search query
            transcript: Video transcript text
            k: Number of candidate keywords to request from LLM
            
        Returns:
            List of Keywords sorted by score/count
        """
        llm_response = await self.llm.extract_keywords(query, transcript, k=k)

        query_is_cjk = self._is_cjk_query(query)

        if not llm_response:
            logger.warning(f"LLM failed for single transcript, using fallback; query: {query}")
            fallback = self._fallback_keywords_from_text(transcript, k=k)
            return self.filter_keywords_by_query_language(fallback, query)

        merged = self.merge_keywords(llm_response, transcript)
        merged = self.filter_low_quality_keywords(merged)
        merged = [kw for kw in merged if self._is_term_compatible_with_query_language(kw.term, query_is_cjk)]
        if merged:
            return merged

        logger.warning(f"LLM returned unusable keywords for single transcript, using fallback; query: {query}")
        fallback = self._fallback_keywords_from_text(transcript, k=k)
        fallback = self.filter_low_quality_keywords(fallback)
        return self.filter_keywords_by_query_language(fallback, query)
    
    async def extract_combined_keywords(
        self,
        query: str,
        transcripts: List[str],
        k: int = 50
    ) -> List[Keyword]:
        """
        Extract keywords from combined transcripts.
        
        Args:
            query: Search query
            transcripts: List of transcript texts
            k: Number of candidate keywords to request from LLM
            
        Returns:
            List of Keywords sorted by score/count
        """
        combined_text = "\n\n---\n\n".join(transcripts)
        
        llm_response = await self.llm.extract_keywords(query, combined_text, k=k)

        query_is_cjk = self._is_cjk_query(query)

        if not llm_response:
            logger.warning(f"LLM failed for combined transcript, using fallback; query: {query}")
            fallback = self._fallback_keywords_from_text(combined_text, k=k)
            return self.filter_keywords_by_query_language(fallback, query)

        merged = self.merge_keywords(llm_response, combined_text)
        merged = self.filter_low_quality_keywords(merged)
        merged = [kw for kw in merged if self._is_term_compatible_with_query_language(kw.term, query_is_cjk)]
        if merged:
            return merged

        logger.warning(f"LLM returned unusable keywords for combined transcript, using fallback; query: {query}")
        fallback = self._fallback_keywords_from_text(combined_text, k=k)
        fallback = self.filter_low_quality_keywords(fallback)
        return self.filter_keywords_by_query_language(fallback, query)
    
    @staticmethod
    def compute_coverage(keywords: List[Keyword], transcripts: List[str]) -> List[Set[int]]:
        """
        Compute which transcripts each keyword appears in.
        
        Args:
            keywords: List of keywords
            transcripts: List of transcript texts
            
        Returns:
            List of sets, where coverage[i] = set of transcript indices containing keywords[i]
        """
        coverage = []
        for kw in keywords:
            transcript_indices = set()
            for idx, text in enumerate(transcripts):
                if KeywordExtractionService.count_occurrences(kw.term, text) > 0:
                    transcript_indices.add(idx)
            coverage.append(transcript_indices)
        return coverage
    
    async def apply_coverage_compensation(
        self,
        combined_keywords: List[Keyword],
        transcripts: List[str],
        per_transcript_keywords: List[List[Keyword]]
    ) -> Tuple[List[Keyword], int]:
        """
        Apply coverage compensation to ensure each transcript is represented.
        
        Algorithm:
        - Select top TOPK keywords from combined
        - Identify uncovered transcripts (no keywords in combined top TOPK)
        - Replace lowest-priority keyword with best keyword from uncovered transcript
        - Protect top CORE_KEEP keywords from replacement
        - Limit to MAX_REPLACE replacements
        
        Args:
            combined_keywords: Sorted combined keywords
            transcripts: List of transcript texts
            per_transcript_keywords: Keywords for each individual transcript
            
        Returns:
            Tuple of (final top TOPK keywords, replacement count)
        """
        if len(combined_keywords) < TOPK:
            logger.warning(f"Combined keywords ({len(combined_keywords)}) < TOPK ({TOPK})")
            return combined_keywords[:TOPK], 0
        
        combined_top = combined_keywords[:TOPK].copy()
        replace_count = 0
        
        for _ in range(MAX_REPLACE):
            # Compute coverage for current combined_top
            coverage = self.compute_coverage(combined_top, transcripts)
            
            # Find first uncovered transcript
            covered_transcripts = set()
            for indices_set in coverage:
                covered_transcripts.update(indices_set)
            
            uncovered_idx = None
            for i in range(len(transcripts)):
                if i not in covered_transcripts:
                    uncovered_idx = i
                    break
            
            if uncovered_idx is None:
                # All transcripts covered
                break
            
            # Find best candidate from uncovered transcript
            uncovered_keywords = per_transcript_keywords[uncovered_idx]
            candidate = None
            for kw in uncovered_keywords:
                if kw.term not in [k.term for k in combined_top]:
                    candidate = kw
                    break
            
            if not candidate:
                # No candidate found
                logger.warning(f"No candidate found for uncovered transcript {uncovered_idx}")
                break
            
            # Find keyword to remove (lowest priority, not in CORE_KEEP)
            # Priority: coverage_count ASC, score ASC, count ASC
            keyword_scores = []
            for idx, kw in enumerate(combined_top):
                if idx < CORE_KEEP:
                    continue  # Protect core keywords
                    
                coverage_count = len(coverage[idx])
                keyword_scores.append((coverage_count, kw.score, kw.count, idx))
            
            if not keyword_scores:
                # Can't remove any (all protected)
                logger.warning("All keywords protected, cannot apply compensation")
                break
            
            # Sort to find lowest priority (smallest coverage, lowest score)
            keyword_scores.sort()
            remove_idx = keyword_scores[0][3]
            
            # Replace
            logger.info(f"Coverage compensation: removing '{combined_top[remove_idx].term}', adding '{candidate.term}'")
            combined_top[remove_idx] = candidate
            
            # Re-sort
            combined_top = sorted(
                combined_top,
                key=lambda k: (-k.score, -k.count, k.term)
            )
            
            replace_count += 1
        
        return combined_top, replace_count
