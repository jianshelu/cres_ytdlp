# Use the base image built from Dockerfile.base
# Replace <GHCR_USER>/<REPO> with actual values or use a build arg
ARG BASE_IMAGE=cres-ytdlp-base:latest
FROM ${BASE_IMAGE}

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir whisperx

# Set model paths as requested
ENV LLM_MODEL_PATH=/workspace/packages/models/llm
ENV WHISPER_MODEL_PATH=/workspace/packages/models/whisperx

# Create model directories
RUN mkdir -p ${LLM_MODEL_PATH} ${WHISPER_MODEL_PATH}

# Copy source code
COPY . .

# Set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default working directory
WORKDIR /home/rama/cres_ytdlp

ENTRYPOINT ["/entrypoint.sh"]
# Default command
CMD ["python3", "main.py"]
