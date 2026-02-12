"""
LLM client for llama.cpp server integration.

This module provides a client to interact with llama-server
running Meta-Llama-3.1-8B-Instruct via OpenAI-compatible API.
"""

import httpx
import json
import logging
import re
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class KeywordCandidate(BaseModel):
    """Keyword candidate from LLM extraction."""
    term: str
    score: float

class LLMKeywordResponse(BaseModel):
    """Response from LLM keyword extraction."""
    query: str
    keywords: List[KeywordCandidate]

class LlamaCppClient:
    """Client for llama.cpp HTTP server."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize llama.cpp client.
        
        Args:
            base_url: Base URL of llama-server (default: http://localhost:8080)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = 5.0  # keep requests short so API can degrade gracefully
        
    def _build_extraction_prompt(self, query: str, text: str, k: int = 50) -> str:
        """
        Build prompt for keyword extraction.
        
        Args:
            query: Search query
            text: Transcript text
            k: Number of keywords to extract
            
        Returns:
            Formatted prompt string
        """
        query_is_cjk = bool(re.search(r"[\u4e00-\u9fff]", query or ""))
        language_rule = (
            "- Output keyword terms in Chinese only. Do not output English keywords.\n"
            if query_is_cjk
            else "- Output keyword terms in the same language as the query.\n"
        )

        return f"""You are an information extraction system.

Task: Extract candidate keywords/phrases that are highly relevant to the search query.

Rules:
- Output MUST be valid JSON only. No markdown, no extra text.
- Provide exactly {k} candidate keywords/phrases.
- Each keyword is 1-5 words/terms, concise, no punctuation.
- Preserve original language script for non-Latin text.
- {language_rule.strip()}
- Prefer specific entities/concepts; avoid generic words (video, today, people, thing).
- Score is semantic relevance to the query on [0,1]. Higher is more relevant.
- Do NOT include counts.
- Do NOT include duplicates (same meaning).

Query: "{query}"

Transcript:
\"\"\"
{text[:8000]}
\"\"\"

Return JSON:
{{
  "query": "{query}",
  "keywords": [
    {{"term":"...", "score":0.0}}
  ]
}}"""

    async def extract_keywords(
        self,
        query: str,
        text: str,
        k: int = 50,
        temperature: float = 0.1,
        max_retries: int = 0
    ) -> Optional[LLMKeywordResponse]:
        """
        Extract keywords from text using LLM.
        
        Args:
            query: Search query
            text: Transcript text
            k: Number of keywords to extract
            temperature: LLM temperature (0.0-1.0)
            max_retries: Number of retry attempts on failure
            
        Returns:
            LLMKeywordResponse with extracted keywords, or None on failure
        """
        prompt = self._build_extraction_prompt(query, text, k)
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that extracts keywords in JSON format."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": k * 30,  # ~30 tokens per keyword entry
            "stream": False
        }
        
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=payload
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Try to extract JSON from response (handle markdown code blocks)
                    content = content.strip()
                    if content.startswith("```"):
                        # Remove markdown code fences
                        lines = content.split("\n")
                        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                    
                    # Parse JSON
                    parsed = json.loads(content)
                    
                    # Validate and return
                    return LLMKeywordResponse(**parsed)
                    
            except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
                logger.warning(f"LLM extraction attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    logger.error(f"All LLM extraction attempts failed for query: {query}")
                    return None
        
        return None
