import asyncio
import sys
sys.path.insert(0, "/workspace")

from src.backend.services.llm_llamacpp import LlamaCppClient

async def test():
    client = LlamaCppClient("http://localhost:8081")
    result = await client.extract_keywords(
        "Oracle", 
        "This is a test about Oracle database and cloud infrastructure", 
        k=5
    )
    print("SUCCESS" if result else "FAILED")
    if result:
        print(f"Query: {result.query}")
        print(f"Keywords: {result.keywords}")
    else:
        print("LLM extraction returned None")

if __name__ == "__main__":
    asyncio.run(test())
