#!/bin/bash
set -euo pipefail

# Backup current runtime image to immutable and rollback-friendly tags.
# Usage:
#   GHCR_IMAGE=ghcr.io/jianshelu/cres_ytdlp:latest ./scripts/backup_ghcr_image.sh

GHCR_IMAGE="${GHCR_IMAGE:-ghcr.io/jianshelu/cres_ytdlp:latest}"
REPO="${GHCR_IMAGE%:*}"
DATE_TAG="$(date +%Y%m%d-%H%M%S)"
BACKUP_TAG="${REPO}:backup-${DATE_TAG}"
LEGACY_TAG="${REPO}:legacy-control-plane-latest"

echo "Pulling source image: ${GHCR_IMAGE}"
docker pull "${GHCR_IMAGE}"

echo "Tagging backup image: ${BACKUP_TAG}"
docker tag "${GHCR_IMAGE}" "${BACKUP_TAG}"

echo "Tagging legacy rollback image: ${LEGACY_TAG}"
docker tag "${GHCR_IMAGE}" "${LEGACY_TAG}"

echo "Pushing backup tags..."
docker push "${BACKUP_TAG}"
docker push "${LEGACY_TAG}"

echo "Backup completed:"
echo "  ${BACKUP_TAG}"
echo "  ${LEGACY_TAG}"
