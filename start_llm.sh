#!/bin/bash
export LLM_MODEL_PATH='/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf'
export LD_LIBRARY_PATH='/app:${LD_LIBRARY_PATH}'
nohup /app/llama-server --model "$LLM_MODEL_PATH" --host 0.0.0.0 --port 8081 -ngl 999 --threads 8 -b 512 > /var/log/llama.log 2>&1 &
echo "LLM Server started."
