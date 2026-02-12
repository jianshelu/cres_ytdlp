#!/bin/bash
set -e

echo "[DEPRECATED] deploy_vast.sh has been archived and must not be used."
echo "Use GHCR immutable deployment: build/push via .github/workflows/deploy.yml, then restart instance with /workspace/start_remote.sh --restart."
echo "Archived script: scripts/archive/legacy_deploy_vast.sh"
exit 1