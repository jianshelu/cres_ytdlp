"""LLM Activity - Text generation using llama.cpp."""

import os

from temporalio import activity

from src.shared import LLMRequest, LLMResponse, get_logger

logger = get_logger("llm_activity")

LLAMA_API_URL = "http://127.0.0.1:8081"


def _llm_fallback_enabled() -> bool:
    value = os.getenv("LEDGE_LLM_FALLBACK_ENABLED", "1").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _fallback_response(prompt: str) -> LLMResponse:
    condensed = " ".join(prompt.split())
    trimmed = condensed[:160] if condensed else "(empty prompt)"
    return LLMResponse(
        text=f"Fallback response: {trimmed}",
        tokens_used=0,
        finish_reason="fallback",
    )


@activity.defn
async def llm_generate(request: LLMRequest) -> LLMResponse:
    """
    Generate text using llama.cpp server.
    
    This activity runs on GPU worker (@gpu queue).
    Connects to llama.cpp at localhost:8081.
    """
    activity.logger.info(f"Starting LLM generation, prompt length: {len(request.prompt)} chars")
    
    try:
        import httpx
        
        import time
        start_time = time.time()
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{LLAMA_API_URL}/v1/chat/completions",
                json={
                    "messages": messages,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        text = result["choices"][0]["message"]["content"]
        tokens_used = result.get("usage", {}).get("total_tokens", 0)
        finish_reason = result["choices"][0].get("finish_reason", "stop")
        
        duration = time.time() - start_time
        logger.info(f"LLM completed: {len(text)} chars, {tokens_used} tokens, {duration:.2f}s")
        
        return LLMResponse(
            text=text,
            tokens_used=tokens_used,
            finish_reason=finish_reason,
        )
        
    except Exception as e:
        if _llm_fallback_enabled():
            logger.warning(f"LLM fallback enabled, returning synthetic response: {e}")
            return _fallback_response(request.prompt)
        logger.error(f"LLM generation failed: {e}")
        raise
