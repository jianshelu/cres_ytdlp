#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/jianshelu/cres_ytdlp}"
BASE_IMAGE="${BASE_IMAGE:-ghcr.io/jianshelu/cres_ytdlp-base:tews-arm64-latest}"
SHA_SHORT="${SHA_SHORT:-$(git rev-parse --short HEAD)}"
LEDGE_SOURCE_SHA="${LEDGE_SOURCE_SHA:-${SHA_SHORT}}"

TEWS_TAG="${IMAGE_NAME}:tews-${SHA_SHORT}"
TEWS_FLOATING_TAG="${IMAGE_NAME}:tews"

echo "[build_tews_arm64] IMAGE_NAME=${IMAGE_NAME}"
echo "[build_tews_arm64] BASE_IMAGE=${BASE_IMAGE}"
echo "[build_tews_arm64] LEDGE_SOURCE_SHA=${LEDGE_SOURCE_SHA}"
echo "[build_tews_arm64] tags: ${TEWS_TAG}, ${TEWS_FLOATING_TAG}"

docker buildx build \
  --platform linux/arm64 \
  --file Dockerfile \
  --build-arg BASE_IMAGE="${BASE_IMAGE}" \
  --build-arg LEDGE_SOURCE_SHA="${LEDGE_SOURCE_SHA}" \
  --push \
  --tag "${TEWS_TAG}" \
  --tag "${TEWS_FLOATING_TAG}" \
  .
