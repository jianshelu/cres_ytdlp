#!/usr/bin/env bash
set -euo pipefail

# Cleanup helper for self-hosted GitHub Actions runner hosts.
# Use with care: this removes stopped/unused Docker artifacts and runner workspace/cache data.

RUNNER_ROOT="${RUNNER_ROOT:-/home/runner/actions-runner}"
RUNNER_SERVICE="${RUNNER_SERVICE:-actions.runner}"
CLEAN_WORKSPACE="${CLEAN_WORKSPACE:-1}"   # 1 = clean _work, 0 = keep
RESTART_SERVICE="${RESTART_SERVICE:-1}"   # 1 = restart runner service

echo "[cleanup] RUNNER_ROOT=$RUNNER_ROOT"
echo "[cleanup] RUNNER_SERVICE=$RUNNER_SERVICE"
echo "[cleanup] CLEAN_WORKSPACE=$CLEAN_WORKSPACE"
echo "[cleanup] RESTART_SERVICE=$RESTART_SERVICE"

echo "[cleanup] disk usage before:"
df -h || true
docker system df || true

if command -v systemctl >/dev/null 2>&1; then
  echo "[cleanup] stopping runner service (best effort): $RUNNER_SERVICE"
  sudo systemctl stop "$RUNNER_SERVICE" || true
fi

echo "[cleanup] removing all containers (best effort)"
docker ps -aq | xargs -r docker rm -f || true

echo "[cleanup] pruning docker images/build cache/volumes"
docker image prune -af || true
docker builder prune -af || true
docker volume prune -f || true
docker network prune -f || true

echo "[cleanup] cleaning runner diagnostics cache"
sudo rm -rf "$RUNNER_ROOT/cached/_diag/"* || true

if [[ "$CLEAN_WORKSPACE" == "1" ]]; then
  echo "[cleanup] cleaning runner workspace (_work)"
  sudo rm -rf "$RUNNER_ROOT/_work/"* || true
else
  echo "[cleanup] skip workspace cleanup"
fi

if [[ "$RESTART_SERVICE" == "1" ]] && command -v systemctl >/dev/null 2>&1; then
  echo "[cleanup] starting runner service"
  sudo systemctl start "$RUNNER_SERVICE" || true
  sudo systemctl status "$RUNNER_SERVICE" --no-pager || true
fi

echo "[cleanup] disk usage after:"
df -h || true
docker system df || true

echo "[cleanup] done"
