#!/bin/bash
set -euo pipefail

SOCK="/var/run/tailscale/tailscaled.sock"
STATE_DIR="/var/lib/tailscale"

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale CLI not found; skipping."
  exit 0
fi

mkdir -p /var/run/tailscale "$STATE_DIR"

if ! pgrep -x tailscaled >/dev/null 2>&1; then
  nohup tailscaled --state="${STATE_DIR}/tailscaled.state" --socket="$SOCK" > /var/log/tailscaled.log 2>&1 &
  sleep 2
fi

if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
  tailscale --socket="$SOCK" up --authkey "${TAILSCALE_AUTHKEY}" --accept-dns=false --accept-routes || true
else
  echo "TAILSCALE_AUTHKEY not provided; tailscale up skipped."
fi

tailscale --socket="$SOCK" ip -4 || true
