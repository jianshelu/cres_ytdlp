# Vast.ai Deployment Guide

## Current Deployment Model (Authoritative)

- Code source of truth: `huihuang` workspace + GitHub repository.
- Runtime artifact source of truth: GHCR images built by `.github/workflows/deploy.yml`.
- Vast instance role: run compute runtime from GHCR image only (no direct code-sync deployment).

Legacy deployment scripts are archived and blocked:

- `scripts/archive/legacy_deploy_vast.sh`
- `scripts/archive/legacy_deploy_vast.py`
- Root stubs `deploy_vast.sh` / `deploy_vast.py` now exit with deprecation notice.

## Where `docker run` Actually Happens

There are only two places in this repo/runtime model:

1. Production runtime on Vast.ai
- Container start is owned by the Vast.ai platform runtime.
- Operator location: Vast.ai Console -> Instance Edit -> Image/Version + On-start script.
- This repo does not run production `docker run` directly for instance startup.

2. CI smoke checks only
- `docker run` appears in:
  - `.github/workflows/deploy.yml`
  - `.github/workflows/ci-minimal-image.yml`
- Those commands are for CI validation, not production instance control.

## Standard Immutable Release Flow

1. Implement/fix code on `huihuang` and commit to GitHub.
2. Trigger `Build and Push to GHCR` workflow.
3. Validate `:canary` on instance.
4. Promote to `:stable` only after validation.
5. Restart runtime on instance (`/workspace/start_remote.sh --restart`) or recreate instance from validated image tag.

## Instance Dependency Policy

- Runtime dependencies must be baked at image build time from `requirements.instance.txt`.
- Do not rely on post-deploy `pip install` for normal operations.

## Single-Flow Incident Handling (No Instance Code Edits)

### Non-code failures (manual operations)

Use these first, without editing code on instance:

1. Service restart/status
- `cd /workspace`
- `./start_remote.sh --status`
- `./start_remote.sh --restart`

2. Worker startup/status
- `supervisorctl -s unix:///tmp/supervisor.sock status`
- `supervisorctl -s unix:///tmp/supervisor.sock start worker-cpu`
- `supervisorctl -s unix:///tmp/supervisor.sock start worker-gpu`

3. Endpoint/env sanity
- Verify `TEMPORAL_ADDRESS`, `MINIO_ENDPOINT`, `MINIO_SECURE` from `/workspace/.env`.
- Ensure instance uses public control-plane endpoints per architecture.

4. Queue health
- Confirm `video-processing@cpu` / `video-processing@gpu` pollers are present.

5. Model/runtime health
- Verify LLM and Whisper model paths under `/workspace/packages/models/...`.
- Check `/var/log/worker.log`, `/var/log/worker-gpu.log`, `/var/log/llama.log`.

### Code-related failures

Do not patch code directly on instance as normal practice.

Use this path:

1. Reproduce and fix on `huihuang` repo.
2. Commit/push.
3. Build GHCR canary.
4. Redeploy instance with new image tag.
5. Re-run smoke/queue checks.

### Emergency hotfix exception

If a temporary instance-side code edit is unavoidable:

1. Record exact changed files and content immediately.
2. Re-apply the same change in `huihuang` repo the same day.
3. Commit and build GHCR image.
4. Redeploy instance from the new image.
5. Remove drift by recreating container/instance or restarting from clean image.

## Verification

- `./start_remote.sh --status` returns healthy services.
- Queue pollers exist for `@cpu` and `@gpu` according to deployment mode.
- No operational step depends on `deploy_vast.sh` or `deploy_vast.py`.
