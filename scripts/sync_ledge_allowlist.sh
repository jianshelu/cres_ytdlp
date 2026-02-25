#!/usr/bin/env bash
set -euo pipefail

SRC_ROOT="${1:-/srv/ledge-repo}"
DST_ROOT="${2:-/srv/project/cres_ytdlp/compute/ledge}"

if [ ! -d "${SRC_ROOT}" ]; then
  echo "Source directory does not exist: ${SRC_ROOT}" >&2
  exit 1
fi

rm -rf "${DST_ROOT}"
mkdir -p "${DST_ROOT}"

(
  cd "${SRC_ROOT}"
  rsync -a --delete --relative \
    src/backend/ \
    src/shared/ \
    src/api/compute/ \
    configs/models.yaml \
    configs/minio.yaml \
    configs/temporal.yaml \
    requirements.instance.txt \
    "${DST_ROOT}/"
)

echo "Synced allowlist from ${SRC_ROOT} to ${DST_ROOT}."
