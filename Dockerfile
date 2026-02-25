# Dockerfile (application image built from prepared runtime base)
ARG BASE_IMAGE=ghcr.io/jianshelu/cres_ytdlp-base:llama-prebuilt-latest
FROM ${BASE_IMAGE} AS base

WORKDIR /workspace

# Python runtime deps are pre-baked in BASE_IMAGE via Dockerfile.base

# Frontend build stage
FROM node:20-slim AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ .
RUN npm run build

# Final stage (inherits Python packages from base stage)
FROM base
WORKDIR /workspace

ARG LEDGE_SOURCE_SHA=unknown
ENV LEDGE_SOURCE_SHA=${LEDGE_SOURCE_SHA}
LABEL org.opencontainers.image.ledge_source_sha="${LEDGE_SOURCE_SHA}"

# Project code and startup scripts
COPY . ./
COPY compute/ledge/ /workspace/ledge-repo/
RUN chmod +x /workspace/entrypoint.sh /workspace/scripts/start-llama.sh /workspace/scripts/with_compute_env.sh /workspace/scripts/container_smoke.sh

# Frontend runtime assets
RUN mkdir -p /workspace/web /workspace/logs /workspace/scripts
COPY --from=frontend-builder /web/.next /workspace/web/.next
COPY --from=frontend-builder /web/public /workspace/web/public
COPY --from=frontend-builder /web/package*.json /workspace/web/
COPY --from=frontend-builder /web/node_modules /workspace/web/node_modules

# Start services through standard profile-aware entrypoint
ENTRYPOINT ["/workspace/entrypoint.sh"]
