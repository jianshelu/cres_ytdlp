# Tasks

## 2026-02-15 (Sunday)
### Docs & Ops (Runbook / Validation / Architecture)
- [ ] Fix GitHub Actions billing/spending-limit block ("recent account payments have failed or your spending limit needs to be increased") so GHCR workflows can run again. (executed: pending)
- [ ] Re-run `Build and Push to GHCR` for `ghcr.io/jianshelu/cres_ytdlp:canary` after billing is unblocked. (executed: pending)

### llama
- [ ] Verify Google Drive sync produced `/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` (regular file, readable, stable size), then restart `llama` and confirm `:8081` listener + `GET /health` OK. (executed: pending)
- [ ] Verify `:canary` image contains required llama shared libs under `/app` (`libllama.so*`, `libggml*.so*`, `libmtmd*.so*`) so `ldd /app/llama-server` has no `not found`. (executed: pending)
- [ ] Publish updated image that extends `LLAMA_WAIT_SECONDS` default to avoid 30-minute llama timeout flapping while post-boot model sync runs. (executed: pending)
- [x] Implement automatic LLM model download in `scripts/start-llama.sh` using `LLM_MODEL_URL` + `.part` + atomic rename into `/workspace/packages/models/llm/`. (executed: 2026-02-15 20:32:00 -05:00)

### Whisper
- [x] Implement transcript min-length filter (`TRANSCRIPT_MIN_CHARS`) in `src/backend/activities.py` to skip degenerate transcripts from batch combined artifacts. (executed: 2026-02-14 20:44:47 -05:00)
- [ ] Re-run `batch wifi densepose` and confirm `queries/wifi-densepose/combined/combined-output.json` excludes the 1-word transcript and no `key_sentences` item equals `\"You\"`. (executed: pending)
- [ ] Tune `TRANSCRIPT_MIN_CHARS` and propagate it to the worker env once validated. (executed: pending)

## 2026-02-14 (Saturday)
### Docs & Ops (Runbook / Validation / Architecture)
- [x] Fix `Dockerfile.base` first-stage `apt-get install` to enforce non-interactive `dpkg` behavior (`DEBIAN_FRONTEND=noninteractive` with `--force-confdef/--force-confold`). (executed: 2026-02-14 16:06:22 -05:00)
- [x] Implement app-image layout validation gate in `.github/workflows/ci-minimal-image.yml` and `.github/workflows/deploy.yml` to fail fast when `/workspace/src` files are missing. (executed: 2026-02-14 16:06:22 -05:00)
- [x] Implement digest-pinned `APP_BASE_IMAGE` resolution in `.github/workflows/deploy.yml` and keep source tag trace as `APP_BASE_IMAGE_TAG`. (executed: 2026-02-14 16:06:22 -05:00)
- [x] Refactor frontend-builder dependency install in `Dockerfile` from `npm install` to lockfile-strict `npm ci`. (executed: 2026-02-14 16:06:22 -05:00)
- [ ] Verify local Docker build/smoke on `huihuang` host with Docker CLI: `docker build -f Dockerfile.base -t cres-base-local .`, `docker run --rm cres-base-local python3 -c "import torch; print(torch.__version__)"`, and `docker run --rm cres-base-local /bin/bash /workspace/scripts/container_smoke.sh`. (executed: pending)
- [ ] Verify `CI Minimal Image Boot` and `Build and Push to GHCR` both pass with new app-layout gates and digest-pinned app base selection. (executed: pending)

### Docker Hub
- [x] Backup GHCR Docker build inputs to `docs/backup/2026-02-14_ghcr_docker_build/`. (executed: 2026-02-14 16:57:25 -05:00)
- [x] Implement Docker Hub publish workflow at `.github/workflows/deploy-dockerhub.yml` targeting `reywang/cres_ytdlp_norfolk`. (executed: 2026-02-14 16:57:25 -05:00)
- [x] Update `Dockerfile`/`Dockerfile.base.prebuilt` default image refs to Docker Hub base tags (`base-llama-*`). (executed: 2026-02-14 16:57:25 -05:00)
- [ ] Configure GitHub Secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` for Docker Hub login. (executed: pending)
- [ ] Seed `base-llama-src-latest` by running workflow `Build and Push to Docker Hub` with `base_variant=llama-src`. (executed: pending)
- [ ] Publish `base-llama-prebuilt-latest` and app `canary` by running workflow `Build and Push to Docker Hub` with `base_variant=llama-prebuilt`. (executed: pending)

### Control API
- [x] Implement role-aware API behavior in `src/api/main.py` using `API_ROLE` so compute hosts reject control-only routes (`/process`, `/batch`, `/admin/reindex`) with `403`. (executed: 2026-02-14 16:06:22 -05:00)
- [x] Fix `/health` role semantics so `API_ROLE=control` reports `llama: n/a` and does not fail control-plane health when llama is absent. (executed: 2026-02-14 16:06:22 -05:00)
- [x] Configure compute FastAPI role in `scripts/supervisord.conf` and `scripts/supervisord_remote.conf` with `API_ROLE="compute"` and document default `API_ROLE=control` in `.env.example`. (executed: 2026-02-14 16:06:22 -05:00)
- [x] Verify role-gate and health behavior using `fastapi.testclient` (`compute` returns `403` on `/process`/`/batch`; `control` returns `200` with `llama: n/a` on `/health`). (executed: 2026-02-14 16:06:22 -05:00)

### Compute API
- [x] Fix `start_remote.sh` to disable default entrypoint fallback and fail fast when supervisor backend is unavailable, preventing duplicate startup chains. (executed: 2026-02-14 16:06:22 -05:00)
- [x] Configure fallback guard in `.env.example` with `ALLOW_ENTRYPOINT_FALLBACK=false` and emergency-rollback guidance. (executed: 2026-02-14 16:06:22 -05:00)
- [x] Verify live instance evidence of duplicate startup chain (`supervisor` + `entrypoint`) and map `cpu@e400b4a529b6` identity to instance host before applying the guard. (executed: 2026-02-14 16:06:22 -05:00)

## 2026-02-13 (Friday)
### Compute API
- [ ] Verify FastAPI crash root cause on GPU instance by collecting `/var/log/fastapi.err` and confirming `src.api.main` import path availability.
- [ ] Fix Vast runtime image target to deploy the app image (with `/workspace/src`) instead of base `.../jupyter` image for compute startup.
- [x] Implement compute boot preflight in `start_remote.sh` to fail fast with explicit diagnostics when `/workspace/src` app files are missing.
- [ ] Test Compute API health on GPU node (`/health`) and confirm dependency checks (`temporal`, `minio`, `llama`) return healthy.

### llama
- [ ] Verify Google Drive model sync postcondition by checking `/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` as a regular readable file with stable non-zero size.
- [ ] Fix model sync flow to download to temporary file and perform atomic rename to `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` only after transfer completion.
- [x] Configure llama startup preflight to fail fast on model-dir write anomalies and emit explicit diagnostics when file checks return inconsistent `exists` states.

### Docs & Ops (Runbook / Validation / Architecture)
- [x] Fix `CI Minimal Image Boot` prebuilt-base resolution to prefer `llama-prebuilt-latest` and fall back through valid GHCR tags before local build.
- [x] Configure explicit Buildx `driver: docker-container` in GHCR deploy workflow jobs that use `type=gha` cache.
- [x] Document GHCR base-selection and Buildx-driver hardening with validation/rollback steps in `docs/PLAN.md`.
- [x] Fix `build-app` Buildx driver to `docker` and remove app GHA cache directives to reduce `/var/lib/buildkit` disk pressure during smoke build.
- [x] Document `ResourceExhausted` disk-fix change and rollback in `docs/PLAN.md`.
- [x] Implement `.agents/skills/frontend/SKILL.md` and `.agents/skills/frontend/REFERENCE.md` for reusable UI/web workflow guidance.
- [ ] Verify `CI Minimal Image Boot` and `Build and Push to GHCR` pass after GHCR base-selection and Buildx-driver updates.
- [ ] Verify `Build and Push to GHCR` no longer fails with `write /var/lib/buildkit/... no space left on device` in `build-app`.
- [x] Configure Vast SSH endpoint rotation in `.env`, `.env.example`, and `docs/Perimeter.md` using the new running instance host/port.
- [x] Verify public-key authentication for the rotated Vast endpoint and keep `VAST_SSH_KEY=~/.ssh/id_huihuang92vastai`.
- [x] Collect Vast instance specs via SSH and refresh `raw_vast.json` observed specs for the new instance.

## 2026-02-12 (Thursday)
### Control Plane (Temporal / MinIO / Web / Control API)
- [x] Implement `web/src/app/audio/page.tsx` to add `/audio` route with server-side data loading from existing `data.json` source.
- [x] Implement `web/src/app/audio/AudioClient.tsx` for audio-focused list/filter UI without changing existing `/video` behavior.
- [x] Implement homepage navigation entry in `web/src/app/page.tsx` to expose the new `Audio` page.
- [x] Configure styles in `web/src/app/globals.css` for audio page layout using existing design tokens.

### Docs & Ops (Runbook / Validation / Architecture)
- [x] Verify `npm run build` in `web/` passes after adding the new route.
- [ ] Test `/audio` page manually on `http://127.0.0.1:3000/audio` and confirm links/playback fall back gracefully when media is missing.
- [ ] Document rollout and rollback steps for the audio page in `docs/PLAN.md` only if API contract or ops behavior changes.
- [x] Collect Vast instance specs via SSH and refresh `raw_vast.json` observed specs.
- [x] Document source-of-truth precedence from `AGENTS.md` `Where the truth lives vividly` in `docs/PLAN.md`.
- [x] Update daily task tracking source references to follow `.agents/skills/triage/SKILL.md` -> `docs/PLAN.md` -> `docs/Task.md` -> `docs/DECISIONS.md`.
- [x] Document Where the truth lives vividly color+emoji interaction requirement for `docs/PLAN.md` and `docs/Task.md` updates (HCI docs scope only).
- [x] Verify `docs/PLAN.md` and `docs/Task.md` vivid formatting standard conformance and update inconsistent wording.
- [x] Archive legacy deploy scripts (`deploy_vast.sh`, `deploy_vast.py`) and block invocation from root stubs.
- [x] Document `docker run` ownership boundaries in `docs/vast_deployment.md` (Vast runtime vs CI smoke only).
- [x] Document immutable single-flow incident handling for instance operations in `docs/vast_deployment.md`.
- [x] Configure SSH access for `ssh2.vast.ai:27139` by setting `VAST_SSH_KEY=~/.ssh/id_huihuang92vastai` in `.env`.
- [x] Implement unified boot script `scripts/start_control_plane_boot.ps1` for Temporal/MinIO/FastAPI startup.
- [x] Configure Task Scheduler `CRES-ControlPlane-Boot` and disable stale split boot tasks.
- [x] Fix committed secret exposure in `scripts/supervisord_remote.conf` by switching to runtime env interpolation.
- [x] Document queue/runtime/security alignment and rollback in `docs/PLAN.md`.
- [x] Document CI smoke endpoint hardening and rollback in `docs/PLAN.md`.
- [x] Optimize `CI Minimal Image Boot` to reuse GHCR base image when base-impacting files are unchanged.
- [x] Configure `Dockerfile.base` runtime base to `vastai/base-image:cuda-12.4.1-auto` with llama runtime preserved via multi-stage copy.
- [x] Fix CUDA stub linker setup in `Dockerfile.base` (`libcuda.so.1` + `rpath-link`) to resolve `cuMem*` undefined-reference build failures.
- [x] Fix `supervisor` install prompt in `Dockerfile.base` with non-interactive `dpkg` options (`--force-confdef --force-confold`) for CI builds.
- [x] Fix base-image pip disk exhaustion by removing `torch` wheel install from `requirements.instance.txt` and validating preinstalled `torch` in `Dockerfile.base`.
- [ ] Verify `CI Minimal Image Boot` and deploy smoke step no longer fail on Temporal DNS resolution.
- [x] Document CI smoke IP readiness guard and rollback in `docs/PLAN.md`.
- [ ] Verify CI smoke envs always resolve to non-empty endpoints (`TEMPORAL_SMOKE_ADDR`, `MINIO_SMOKE_ENDPOINT`) before app boot.

### Workers & Queues (@cpu / @gpu)
- [x] Fix queue routing names to `<base>@cpu` and `<base>@gpu` in `src/api/main.py`, `src/backend/workflows.py`, and `src/backend/worker.py`.
- [x] Fix `src/backend/worker.py` to allow `WORKER_MODE=cpu` startup without requiring `torch`.
- [x] Fix queue references in operational scripts (`scripts/container_smoke.sh`, `scripts/rerun_failed_workflows.py`) to use the new suffix routing.
- [x] Verify `video-processing@cpu` pollers are registered in Temporal (`huihuang@cpu` workflow/activity).
- [x] Verify worker pollers register on `video-processing@cpu` and `video-processing@gpu` after restart.
- [x] Deploy code snapshot and install `requirements.instance.txt` on ssh2 instance for GPU worker runtime.
- [x] Fix temp cleanup race in `src/backend/activities.py` to avoid deleting active transfer temp files (`.part/.part.minio`).
- [x] Fix CI smoke dependency endpoint injection to use resolved container IPs in `.github/workflows/ci-minimal-image.yml` and `.github/workflows/deploy.yml`.
- [x] Fix CI smoke dependency IP readiness race by adding retry/guard checks in `.github/workflows/ci-minimal-image.yml` and `.github/workflows/deploy.yml`.

### Resource & Performance (RAM / VRAM / Batch / Threads)
- [x] Fix runtime defaults for llama to `-ngl 999 --threads 8 -b 512` in `entrypoint.sh` and `start_llm.sh`.
- [x] Fix worker/llama memory caps in `scripts/supervisord_remote.conf` to align with triage baseline (`4GB` workers / `3GB` llama).
- [x] Implement active-instance scheduling caps in `src/api/main.py` (`SCHEDULER_ACTIVE_INSTANCE`, `SCHEDULER_ACTIVE_MAX_PARALLELISM`).
- [ ] Test batch scheduling throughput on active instance and tune `SCHEDULER_ACTIVE_MAX_PARALLELISM` if instance profile changes.

### Networking & NAT (64.229.113.233 / Port Forwarding)
- [x] Fix `.env.example` control-plane endpoints to current NAT/public defaults (`64.229.113.233`).

## 2026-02-11 (Wednesday)
### Docs & Ops (Runbook / Validation / Architecture)
- [x] Document canonical project root as `C:\Users\rama\cres_ytdlp_norfolk` and archive path at `C:\Users\rama\_archive\legacy_root_project_20260211_215608`.
- [x] Verify web service responds at `http://127.0.0.1:3000` after launcher restart.
- [x] Verify ports `3000` (web) and `8000` (FastAPI) are listening.
- [x] Document rollback runbook for restoring archived root copy and rerunning launchers.

## 2026-02-10 (Tuesday)
### Control Plane (Temporal / MinIO / Web / Control API)
- [x] Implement transcriptions API limit increase from `5` to `50` in `src/api/routers/transcriptions.py`.
- [x] Implement frontend query limit alignment in `web/src/app/transcriptions/page.tsx` and `web/src/app/sentence/page.tsx`.
- [x] Implement Next API proxy default limit update to `50` in `web/src/app/api/transcriptions/route.ts`.
- [x] Implement transcriptions UI text update from `max 5` to `max 50` in `web/src/app/transcriptions/TranscriptionsClient.tsx`.
- [ ] Verify playback/UI smoke and workflow throughput after limit expansion.

### Docs & Ops (Runbook / Validation / Architecture)
- [x] Document runtime rule to avoid WSL and prefer Conda on Norfolk/huihuang.
- [x] Document architecture rule that control plane runs on huihuang and compute runs on Vast.ai GPU instance.
- [ ] Document and keep instance-local Temporal/MinIO disabled for the current topology.
- [ ] Document hybrid runtime migration summary and artifact status update.

### Networking & NAT (64.229.113.233 / Port Forwarding)
- [ ] Configure SSH configs for Vast.ai and huihuang with current host/IP values.
- [ ] Verify connectivity to both hosts after SSH config updates.
- [ ] Document latest IP/port mapping in perimeter/runbook docs.
- [x] Configure Vast SSH endpoint rotation to `ssh2.vast.ai:27139` in `.env`, `.env.example`, and `docs/Perimeter.md`.
- [x] Verify public-key authentication for `ssh -p 15307 root@ssh3.vast.ai -L 8080:localhost:8080`.

### Workers & Queues (@cpu / @gpu)
- [ ] Verify Temporal monitoring results for 30 workflows (`turbo-all`).
- [ ] Verify MinIO artifacts exist for newly produced videos (`turbo-all`).
- [ ] Verify `data.json` refresh on huihuang after workflow completion.
- [ ] Deploy GHCR canary image to Vast.ai instance and verify worker restart behavior without code sync scripts.

## 2026-02-06 (Thursday)
### Networking & NAT (64.229.113.233 / Port Forwarding)
- [ ] Configure SSH tunnel with port `8080` forwarding.
- [ ] Deploy GHCR image update to remote runtime and verify immutable rollout.
- [ ] Verify remote service behavior after sync.

### GPU Instance (llama / Whisper / Compute API)
- [ ] Implement GPU-accelerated video decoding (FFmpeg NVDEC).

### Control Plane (Temporal / MinIO / Web / Control API)
- [ ] Implement transcriptions page combined section + carousel follow-up.
- [ ] Test transcriptions backend endpoint with `curl`.
- [ ] Verify carousel navigation and combined keyword rendering.

### Docs & Ops (Runbook / Validation / Architecture)
- [ ] Document cookies upload requirement to unblock restricted downloads.
- [ ] Deploy re-trigger of failed "Oracle" workflows.
- [ ] Verify successful download and transcription for retried Oracle workflows.
- [x] Document migration of legacy ledger items into structured Task.md sections.


