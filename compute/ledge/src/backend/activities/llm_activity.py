"""LLM Activity - Text generation using llama.cpp."""

from temporalio import activity

from src.shared import LLMRequest, LLMResponse, get_logger

logger = get_logger("llm_activity")

LLAMA_API_URL = "http://127.0.0.1:8081"


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
        logger.error(f"LLM generation failed: {e}")
        raise
