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
    def normalize_term(term: str) -> str:
        """
        Normalize keyword term (lowercase, remove punctuation).
        
        Args:
            term: Raw keyword term
            
        Returns:
            Normalized term
        """
        # Lowercase and remove punctuation
        term = term.lower().strip()
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
        pattern = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
        return len(pattern.findall(text))
    
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
        
        if not llm_response:
            logger.warning(f"LLM failed for single transcript, query: {query}")
            return []
        
        return self.merge_keywords(llm_response, transcript)
    
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
        
        if not llm_response:
            logger.warning(f"LLM failed for combined transcript, query: {query}")
            return []
        
        return self.merge_keywords(llm_response, combined_text)
    
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
