"""
Combined sentence extraction service.

This module extracts sentences containing combined keywords
and merges them into a single paragraph without modification.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

class SentenceService:
    """Service for extracting and combining sentences."""
    
    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Split on sentence-ending punctuation followed by space/newline
        # Handles: . ! ? 。 ！ ？
        sentences = re.split(r'[.!?。！？]+[\s\n]+', text)
        
        # Clean and filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    @staticmethod
    def find_sentence_with_keyword(sentences: List[str], keyword: str) -> str | None:
        """
        Find first sentence containing keyword (case-insensitive, word boundary).
        
        Args:
            sentences: List of sentences to search
            keyword: Keyword to find
            
        Returns:
            First matching sentence, or None if not found
        """
        pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
        
        for sentence in sentences:
            if pattern.search(sentence):
                return sentence
        
        return None
    
    @staticmethod
    def extract_combined_sentence(
        combined_text: str,
        keywords: List[str],
        max_sentences: int = 5
    ) -> str:
        """
        Extract sentences containing each keyword and merge them.
        
        Args:
            combined_text: Combined transcription text
            keywords: List of keyword terms (already top-5)
            max_sentences: Maximum number of sentences to include (default: 5)
            
        Returns:
            Merged sentence paragraph
        """
        sentences = SentenceService.split_sentences(combined_text)
        
        # Extract evidence sentences (one per keyword)
        evidence_sentences = []
        seen_sentences = set()
        
        for keyword in keywords[:max_sentences]:
            sentence = SentenceService.find_sentence_with_keyword(sentences, keyword)
            
            if sentence and sentence not in seen_sentences:
                evidence_sentences.append(sentence)
                seen_sentences.add(sentence)
        
        if not evidence_sentences:
            logger.warning("No evidence sentences found for keywords")
            return ""
        
        # Join sentences with period + space
        combined_sentence = ". ".join(evidence_sentences)
        
        # Ensure final period
        if not combined_sentence.endswith(('.', '!', '?', '。', '！', '？')):
            combined_sentence += "."
        
        return combined_sentence
