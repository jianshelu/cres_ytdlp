# Dockerfile (supervisord PID1; starts all services)
ARG BASE_IMAGE=ghcr.io/jianshelu/cres_ytdlp-base:latest
FROM ${BASE_IMAGE} AS base

WORKDIR /workspace

# Install Python deps (instance runtime only: FastAPI + worker CPU/GPU stack)
COPY requirements.instance.txt .
RUN pip3 install --upgrade pip \
 && pip3 install --no-cache-dir -r requirements.instance.txt \
 && rm -rf /root/.cache/pip \
 && find /usr/local/lib/python3.10/dist-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
 && find /usr/local/lib/python3.10/dist-packages -type f -name "*.pyc" -delete \
 && find /usr/local/lib/python3.10/dist-packages -type f -name "*.pyo" -delete

# Frontend build stage
FROM node:20-slim AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm install
COPY web/ .
RUN npm run build

# Final stage (inherits Python packages from base stage)
FROM base
WORKDIR /workspace

# Project code and root scripts
COPY . ./

# Frontend runtime assets
RUN mkdir -p /workspace/web
COPY --from=frontend-builder /web/.next /workspace/web/.next
COPY --from=frontend-builder /web/public /workspace/web/public
COPY --from=frontend-builder /web/package*.json /workspace/web/
COPY --from=frontend-builder /web/node_modules /workspace/web/node_modules

# Start all services via supervisord (single-container, self-healing)
ENTRYPOINT ["/usr/bin/supervisord","-n","-c","/etc/supervisor/supervisord.conf"]
