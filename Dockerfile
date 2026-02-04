# ARG for base image (passed from CI)
ARG BASE_IMAGE=ghcr.io/ggml-org/llama.cpp:server-cuda
FROM node:20-slim AS frontend-builder
WORKDIR /workspace
# Copy web specific files
COPY web/package*.json ./
RUN npm install
COPY web/ .
RUN npm run build

# Final Stage
FROM ${BASE_IMAGE}

WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy Backend Scripts
COPY batch_process.py .
COPY generate_index.py .
COPY scripts/ scripts/
COPY src/ src/

# Copy Frontend Build into /workspace/web
COPY --from=frontend-builder /workspace/.next ./web/.next
COPY --from=frontend-builder /workspace/public ./web/public
COPY --from=frontend-builder /workspace/node_modules ./web/node_modules
# Copy web package.json for start script
COPY --from=frontend-builder /workspace/package.json ./web/package.json

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3000 8000 8081 7233 9000 9001

ENTRYPOINT ["/entrypoint.sh"]
# Default command starts Next.js and keeps container alive
CMD ["npm", "start", "--prefix", "web"]
