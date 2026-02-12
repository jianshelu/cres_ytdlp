# --- Frontend Build Stage ---
FROM node:20-slim AS frontend-builder
WORKDIR /workspace
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# --- Final Image Stage ---
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
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for running the frontend in production)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Temporal CLI
RUN curl -sSf https://temporal.download/cli.sh | sh && \
    mv /root/.temporalio/bin/temporal /usr/local/bin/

# Install MinIO and mc
RUN wget https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio && \
    chmod +x /usr/local/bin/minio && \
    curl -L https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc

# Set environment variables
ENV PATH="/workspace:${PATH}" \
    PYTHONUNBUFFERED=1 \
    LLM_MODEL_PATH=/workspace/packages/models/llm \
    WHISPER_MODEL_PATH=/workspace/packages/models/whisper \
    XDG_CACHE_HOME=/workspace/.cache

# Setup directories
WORKDIR /workspace
RUN mkdir -p ${LLM_MODEL_PATH} ${WHISPER_MODEL_PATH} /data/minio /workspace/.cache

# Install Python dependencies with CUDA optimization
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu121 && \
    pip3 install --no-cache-dir -r requirements.txt

# Pre-cache Whisper models
COPY setup_models.py .
RUN python3 setup_models.py

# Copy Frontend Build and Source Code
COPY --from=frontend-builder /workspace/.next ./.next
COPY --from=frontend-builder /workspace/public ./public
COPY --from=frontend-builder /workspace/node_modules ./node_modules
COPY . .

# Set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3000 8081 7233 9000 9001

ENTRYPOINT ["/entrypoint.sh"]
# Default command starts the Next.js app and the pipeline main script
CMD ["sh", "-c", "npm start & python3 src/worker.py"]
