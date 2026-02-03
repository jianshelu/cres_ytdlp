# Use pre-compiled llama.cpp server image (CUDA 12.4)
FROM ghcr.io/ggml-org/llama.cpp:server-cuda

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    curl \
    wget \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Temporal CLI
RUN curl -sSf https://temporal.download/cli.sh | sh && \
    mv /root/.temporalio/bin/temporal /usr/local/bin/

# Install MinIO and mc
RUN wget https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio && \
    chmod +x /usr/local/bin/minio && \
    curl -L https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc

# Set environment variables
ENV PATH="/app:${PATH}" \
    LD_LIBRARY_PATH="/app:${LD_LIBRARY_PATH}" \
    PYTHONUNBUFFERED=1 \
    LLM_MODEL_PATH=/workspace/packages/models/llm \
    WHISPER_MODEL_PATH=/workspace/packages/models/whisperx

# Setup directories
WORKDIR /workspace
RUN mkdir -p ${LLM_MODEL_PATH} ${WHISPER_MODEL_PATH} /data/minio

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir whisperx

# Copy source code
COPY . .

# Set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "main.py"]
