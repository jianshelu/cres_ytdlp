# Tasks

## 2026-02-13 (Friday)
### Compute API
- [ ] Verify FastAPI crash root cause on GPU instance by collecting `/var/log/fastapi.err` and confirming `src.api.main` import path availability.
- [ ] Fix Vast runtime image target to deploy the app image (with `/workspace/src`) instead of base `.../jupyter` image for compute startup.
- [ ] Test Compute API health on GPU node (`/health`) and confirm dependency checks (`temporal`, `minio`, `llama`) return healthy.

### llama
- [ ] Verify Google Drive model sync postcondition by checking `/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` as a regular readable file with stable non-zero size.
- [ ] Fix model sync flow to download to temporary file and perform atomic rename to `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` only after transfer completion.
- [ ] Configure llama startup preflight to fail fast on model-dir write anomalies and emit explicit diagnostics when file checks return inconsistent `exists` states.

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
- [x] Verify public-key authentication for the rotated Vast endpoint and keep `VAST_SSH_KEY=~/.ssh/id_huihuang2vastai`.
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
- [x] Update daily task tracking source references to follow `.agents/skills/cres-triage/SKILL.md` -> `docs/PLAN.md` -> `docs/Task.md` -> `docs/DECISIONS.md`.
- [x] Document Where the truth lives vividly color+emoji interaction requirement for `docs/PLAN.md` and `docs/Task.md` updates (HCI docs scope only).
- [x] Verify `docs/PLAN.md` and `docs/Task.md` vivid formatting standard conformance and update inconsistent wording.
- [x] Archive legacy deploy scripts (`deploy_vast.sh`, `deploy_vast.py`) and block invocation from root stubs.
- [x] Document `docker run` ownership boundaries in `docs/vast_deployment.md` (Vast runtime vs CI smoke only).
- [x] Document immutable single-flow incident handling for instance operations in `docs/vast_deployment.md`.
- [x] Configure SSH access for `ssh2.vast.ai:27139` by setting `VAST_SSH_KEY=~/.ssh/id_huihuang2vastai` in `.env`.
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

