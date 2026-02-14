# PLAN
## 2026-02-14 - Fix MinIO Credential Drift Between Template Env and /workspace/.env

- Objective: prevent GPU worker from starting with wrong MinIO credentials due to silent fallback or stale `.env` overrides.
- Root cause:
  - `scripts/with_compute_env.sh` allowed fallback to `minioadmin` when `MINIO_*` and AWS aliases were absent, causing wrong-key runtime behavior instead of explicit failure.
  - `start_remote.sh` sourced `/workspace/.env` unconditionally, which could override runtime-injected credentials from Vast template env.
- Changes:
  - `scripts/with_compute_env.sh`
    - Removed `minioadmin` default fallback for `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`.
    - Kept AWS alias mapping (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SECRET_KEY_ID`) as fallback source only.
    - Added fail-fast guard: exit with clear error when resolved `MINIO_*` credentials are missing.
  - `start_remote.sh`
    - Updated `load_workspace_env()` to preserve runtime-injected sensitive keys while sourcing `/workspace/.env`.
    - Preserved keys:
      - `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
      - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SECRET_KEY_ID`
      - `TEMPORAL_ADDRESS`, `MINIO_ENDPOINT`, `MINIO_SECURE`

### Validation

- Verify no default `minioadmin` fallback remains:
  - `rg --line-number "minioadmin|missing MINIO_ACCESS_KEY" scripts/with_compute_env.sh`
- Verify env-preserve logic in `start_remote.sh`:
  - `rg --line-number "snapshot_file|sensitive_keys|Preserve runtime-injected env" start_remote.sh`
- Runtime check on instance (redacted):
  - Compare worker-gpu env vs `/workspace/.env` by hash only (no secret output).
  - Confirm worker does not start with default `minioadmin` unless explicitly configured.

### Rollback

1. Restore previous `minioadmin` fallback lines in `scripts/with_compute_env.sh`.
2. Revert `load_workspace_env()` preservation block in `start_remote.sh`.
3. Rebuild and redeploy previous app image tag.

## 2026-02-14 - Prevent False Supervisor-Healthy Detection on Cold Boot

- Objective: avoid startup drift where `start_remote.sh` skips supervisor bootstrap due to false-positive backend detection.
- Root cause:
  - `supervisor_controls_backend()` treated non-empty `supervisorctl status` output as success.
  - On some instances, stale socket/transport errors produced non-empty text, causing a false "supervisor is managing backend" branch.
- Changes:
  - `start_remote.sh`
    - `supervisor_status_raw()` now returns real `supervisorctl` exit code (removed `|| true`).
    - `supervisor_controls_backend()` now:
      - requires successful `supervisorctl` command execution;
      - requires non-empty output;
      - requires at least one valid supervisor program status line (`RUNNING|STARTING|BACKOFF|STOPPED|FATAL|EXITED|UNKNOWN`).
    - This ensures cold boot reliably enters `ensure_supervisor_backend()` when supervisor is not actually active.

### Validation

- Syntax check:
  - `bash -n start_remote.sh`
- Verify guard logic:
  - `rg --line-number "supervisor_status_raw|supervisor_controls_backend|RUNNING\\|STARTING\\|BACKOFF" start_remote.sh`
- Runtime check on new instance:
  - `tail -n 120 /var/log/onstart.log`
  - `supervisorctl -s unix:///tmp/supervisor.sock status`
  - `ps -eo pid,lstart,etime,cmd | grep supervisord`

### Rollback

1. Restore previous `supervisor_status_raw()` (`... || true`).
2. Remove strict status-line pattern validation in `supervisor_controls_backend()`.
3. Redeploy previous app image tag.

## 2026-02-14 - Rollback: Keep CPU Worker on `huihuang` by Default

- Objective: revert the topology change that moved `@cpu` worker ownership to instance-only.
- Changes:
  - `scripts/start_control_plane_boot.ps1`
    - Removed `CONTROL_PLANE_ENABLE_LOCAL_CPU_WORKER` gating logic.
    - Restored default behavior: start/keep local CPU worker on `huihuang`.
  - `scripts/supervisord.conf`
    - Restored `[program:worker-cpu] autostart=false`.
  - `scripts/supervisord_remote.conf`
    - Restored `[program:worker-cpu] autostart=false`.
  - `.env.example`
    - Removed `CONTROL_PLANE_ENABLE_LOCAL_CPU_WORKER` example entry.

### Validation

- Run control-plane boot:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_control_plane_boot.ps1`
- Confirm local worker exists:
  - `Get-CimInstance Win32_Process | ? { $_.CommandLine -match "src\\.backend\\.worker" }`
- Confirm Temporal pollers include `cpu@huihuang` on `video-processing@cpu`.

### Rollback

1. Re-apply instance-only CPU ownership change if needed (local CPU disable gate + instance CPU autostart).
2. Re-run boot/startup scripts and verify pollers.

## 2026-02-14 - Worker Identity Uses `role@instance_name`

- Objective: make poller identity easier to read and align with operator expectation (`cpu@instance`, `gpu@instance`).
- Root cause:
  - Worker identity format was `<host>@cpu` / `<host>@gpu`, which made role-first scanning harder in Temporal poller views.
- Changes:
  - `src/backend/worker.py`
    - Changed identity format to:
      - `cpu@<instance_name>`
      - `gpu@<instance_name>`
    - Added optional env override:
      - `WORKER_INSTANCE_NAME` (defaults to hostname when unset).
  - `.env.example`
    - Added optional `WORKER_INSTANCE_NAME` comment.

### Validation

- Restart workers on control-plane/instance.
- Check Temporal pollers:
  - `video-processing@cpu` should show identities like `cpu@huihuang` or `cpu@<instance>`.
  - `video-processing@gpu` should show identities like `gpu@<instance>`.
- Optional override test:
  - Set `WORKER_INSTANCE_NAME=my-instance`, restart worker, confirm identity becomes `cpu@my-instance`/`gpu@my-instance`.

### Rollback

1. Revert identity strings in `src/backend/worker.py` to `<hostname>@cpu` / `<hostname>@gpu`.
2. Remove optional `WORKER_INSTANCE_NAME` comment from `.env.example`.

## 2026-02-14 - Move `@cpu` Worker Ownership to Instance by Default

- Objective: enforce compute topology so both `@cpu` and `@gpu` workers run on the Vast instance, while `huihuang` remains control-plane only.
- Root cause:
  - `scripts/start_control_plane_boot.ps1` auto-started local `WORKER_MODE=cpu` on `huihuang`, producing `huihuang@cpu` pollers.
  - Instance supervisor default had `worker-cpu` disabled in main image config.
- Changes:
  - `scripts/start_control_plane_boot.ps1`
    - Added `CONTROL_PLANE_ENABLE_LOCAL_CPU_WORKER` gate (default `false` when absent).
    - When disabled, script stops any existing local CPU worker and skips local worker startup.
  - `scripts/supervisord.conf`
    - Set `[program:worker-cpu] autostart=true` so instance starts `@cpu` worker automatically.
  - `scripts/supervisord_remote.conf`
    - Set `[program:worker-cpu] autostart=true`.
    - Set `[program:worker-gpu] autostart=true` to keep both queues managed by supervisor on remote path.
  - `.env.example`
    - Added `CONTROL_PLANE_ENABLE_LOCAL_CPU_WORKER=false`.

### Validation

- Local control plane:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_control_plane_boot.ps1`
  - Confirm no local worker process:
    - `Get-CimInstance Win32_Process | ? { $_.CommandLine -match "src\\.backend\\.worker" }`
- Instance:
  - `supervisorctl -s unix:///tmp/supervisor.sock status`
  - Expect `worker-cpu` and `worker-gpu` in `RUNNING`.
- Temporal:
  - `video-processing@cpu` pollers should be instance identities only (no `huihuang@cpu`).

### Rollback

1. Revert `scripts/start_control_plane_boot.ps1` worker gating block.
2. Revert `autostart` values in `scripts/supervisord.conf` and `scripts/supervisord_remote.conf`.
3. Remove `CONTROL_PLANE_ENABLE_LOCAL_CPU_WORKER` from `.env.example`.
4. Re-run control-plane boot and verify `huihuang@cpu` returns if desired.

## 2026-02-14 - Harden Vast On-Start MinIO Credential Handling

- Objective: prevent silent GPU activity retry loops when Vast template env uses inconsistent AWS/MinIO key names.
- Root cause:
  - Vast template invocations sometimes provide `AWS_SECRET_KEY_ID` (typo) instead of `AWS_SECRET_ACCESS_KEY`.
  - When MinIO credentials are missing/misaligned at boot, GPU worker starts but `transcribe_video` repeatedly fails with `InvalidAccessKeyId`.
- Changes:
  - `onstart.sh`
    - Added env alias normalization:
      - `AWS_SECRET_KEY_ID -> AWS_SECRET_ACCESS_KEY`
      - fallback mapping between `AWS_*` and `MINIO_*` credentials.
    - Added fail-fast guard:
      - abort startup with explicit log error when `MINIO_ACCESS_KEY` or `MINIO_SECRET_KEY` is missing.

### Validation

- `bash -n onstart.sh`
- Boot-time log check on instance:
  - `sed -n '1,120p' /var/log/onstart.log`
- Runtime env check:
  - `env | grep -E '^(MINIO_ACCESS_KEY|MINIO_SECRET_KEY|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)='`
- Temporal queue check:
  - `video-processing@gpu` poller exists and no new `InvalidAccessKeyId` in worker logs.

### Rollback

1. Revert credential normalization/fail-fast block in `onstart.sh`.
2. Redeploy previous image/tag.
3. Restart instance and re-check `/var/log/onstart.log` plus GPU worker queue pollers.

## 2026-02-14 - Rotate Vast SSH Endpoint to `ssh7.vast.ai:17568` (Recreated Instance)

- Objective: switch tooling to the recreated Vast.ai instance and restore GPU queue polling path.
- Changes:
  - `.env`
    - `VAST_HOST=ssh7.vast.ai`
    - `VAST_PORT=17568`
  - `.env.example`
    - `VAST_HOST=ssh7.vast.ai`
    - `VAST_PORT=17568`
- Validation:
  - SSH connectivity:
    - `ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i ~/.ssh/id_huihuang2vastai -p 17568 root@ssh7.vast.ai "hostname; whoami"`
  - GPU activity poller recovered on Temporal:
    - `D:\soft\temporal.exe task-queue describe --address 127.0.0.1:7233 --namespace default --task-queue video-processing@gpu --task-queue-type activity`
    - Observed poller identity: `61f9310790fb@gpu`
- Rollback:
  1. Revert `VAST_HOST` / `VAST_PORT` in `.env` and `.env.example` to previous values.
  2. Re-run SSH validation against previous endpoint.

## 2026-02-13 - Make Vast Startup Prefer Supervisor Backend and Remove Entry Drift

- Objective: ensure Vast boot path consistently uses the same supervisor-managed runtime as container image entrypoint.
- Root cause:
  - `start_remote.sh` only treated supervisor as active when `fastapi` was already `RUNNING`; otherwise it fell back to `entrypoint.sh`.
  - This created runtime drift from `scripts/supervisord.conf` and could bypass dedicated `worker-gpu` process wiring.
  - `onstart.sh` invoked `./start_remote.sh` directly; using `bash` is safer against exec-bit inconsistencies.
- Changes:
  - `start_remote.sh`
    - Added supervisor helpers:
      - `supervisor_status_raw`
      - `detect_supervisor_conf`
      - `ensure_supervisor_backend`
    - Updated `supervisor_controls_backend` to treat non-empty supervisor status as backend-managed (no strict `fastapi RUNNING` gate).
    - `restart_services` now calls `ensure_supervisor_backend` first and prefers supervisor path; only falls back to `entrypoint` when supervisor is unavailable.
    - `show_status` now prints supervisor program status when available.
  - `onstart.sh`
    - Updated start invocation from `./start_remote.sh` to `bash ./start_remote.sh`.

### Validation

- Syntax check:
  - `bash -n start_remote.sh`
  - `bash -n onstart.sh`
- Verify supervisor-first logic:
  - `rg --line-number "ensure_supervisor_backend|detect_supervisor_conf|SUPERVISOR_SOCKET|Supervisor backend unavailable" start_remote.sh`
- Runtime verification on Vast instance (read-only):
  - `tail -n 120 /var/log/onstart.log`
  - `supervisorctl -s unix:///tmp/supervisor.sock status`
  - `ss -ltnp | grep -E ":8000|:8081"`

### Rollback

1. Revert `start_remote.sh` to previous supervisor detection and entrypoint fallback behavior.
2. Revert `onstart.sh` invocation back to `./start_remote.sh`.
3. Redeploy previous image tag if needed.

## 2026-02-13 - Harden Vast Startup and llama Runtime Lib Packaging for New Instance Boot

- Objective: prevent compute container boot failure on new Vast instances and eliminate missing `llama-server` shared-lib errors.
- Root cause:
  - Vast launch script executes `/workspace/onstart.sh` directly; non-executable mode caused `Permission denied` and blocked supervisor startup.
  - llama artifacts copy in `Dockerfile.base` previously copied only regular files, so SONAME symlinks (`*.so.0`) and some linked libs could be absent in runtime.
- Changes:
  - `Dockerfile`
    - After `COPY . ./`, added:
      - `RUN chmod +x /workspace/onstart.sh /workspace/start_remote.sh /workspace/entrypoint.sh`
    - This makes startup robust even when Vast on-start uses direct script execution.
  - `Dockerfile.base`
    - Updated llama artifact copy discovery from `-type f` to `\( -type f -o -type l \)` for:
      - `libllama.so*`
      - `libggml*.so*`
      - `libmtmd*.so*`
    - This preserves required runtime symlinks used by dynamic loader resolution.

### Validation

- Verify startup script hardening:
  - `rg --line-number "chmod \\+x /workspace/onstart\\.sh /workspace/start_remote\\.sh /workspace/entrypoint\\.sh" Dockerfile`
- Verify symlink-aware llama lib packaging:
  - `rg --line-number "\\( -type f -o -type l \\).*lib(llama|ggml|mtmd)" Dockerfile.base`
- Post-build instance checks (read-only):
  - `ls -l /workspace/onstart.sh`
  - `ldd /app/llama-server | grep -E "not found|libmtmd|libllama|libggml"`
  - `supervisorctl status`

### Rollback

1. Remove the `chmod +x` line from `Dockerfile`.
2. Revert the three `find` expressions in `Dockerfile.base` from `\( -type f -o -type l \)` back to `-type f`.
3. Rebuild and redeploy previous image tags.

## 2026-02-13 - Keep Compute Env Wrapper Coherent with Docker Base/App Build Triggers

- Objective: ensure new compute env wrapper changes are always reflected in published images and base runtime files.
- Root cause:
  - `scripts/supervisord.conf` now invokes `scripts/with_compute_env.sh`, but base Dockerfiles did not copy that script.
  - Build workflow path filters did not include `scripts/with_compute_env.sh`, so wrapper-only changes could skip image rebuild.
- Changes:
  - `Dockerfile.base`
    - Copy `scripts/with_compute_env.sh` into `/workspace/scripts/with_compute_env.sh`.
    - Mark wrapper executable together with `start-llama.sh`.
  - `Dockerfile.base.prebuilt`
    - Copy `scripts/with_compute_env.sh` into `/workspace/scripts/with_compute_env.sh`.
    - Mark wrapper executable together with `start-llama.sh`.
  - `.github/workflows/deploy.yml`
    - Added `scripts/with_compute_env.sh` to `on.push.paths`.
    - Added `scripts/with_compute_env.sh` to base-impact path filter.
  - `.github/workflows/ci-minimal-image.yml`
    - Added `scripts/with_compute_env.sh` to base-impact path filter.

### Validation

- Verify wrapper is copied by both base routes:
  - `rg --line-number "with_compute_env\\.sh" Dockerfile.base Dockerfile.base.prebuilt`
- Verify deploy workflow trigger/filter include wrapper:
  - `rg --line-number "scripts/with_compute_env\\.sh" .github/workflows/deploy.yml`
- Verify CI minimal base-impact filter includes wrapper:
  - `rg --line-number "scripts/with_compute_env\\.sh" .github/workflows/ci-minimal-image.yml`

### Rollback

1. Revert wrapper copy/chmod lines in `Dockerfile.base` and `Dockerfile.base.prebuilt`.
2. Remove `scripts/with_compute_env.sh` from workflow path/filter lists.
3. Re-run workflow and confirm previous trigger behavior is restored.

## 2026-02-13 - Persist GPU Worker Endpoint Defaults and Autostart in Local Codebase

- Objective: remove instance-only drift by persisting the queue-unblock fix into repo-managed runtime config.
- Root cause:
  - Runtime recovery on instance used manual worker launch and was not durable across container restarts.
  - Image runtime uses `scripts/supervisord.conf` (from `Dockerfile.base`), where workers inherited localhost defaults and `worker-gpu` was not autostarted.
- Changes:
  - `scripts/with_compute_env.sh` (new)
    - Added split-host-safe defaults for compute runtime env:
      - `TEMPORAL_ADDRESS=64.229.113.233:7233`
      - `MINIO_ENDPOINT=64.229.113.233:9000`
      - `MINIO_SECURE=false`
    - Added MinIO/AWS credential alias normalization so worker/activity code sees consistent variables.
  - `scripts/supervisord.conf`
    - Updated `fastapi`, `worker-cpu`, and `worker-gpu` commands to execute through `scripts/with_compute_env.sh`.
    - Enabled `worker-gpu` autostart (`autostart=true`) to avoid `@gpu` queue stall on fresh boot.
  - `onstart.sh`
    - Updated stale endpoint defaults (`100.121.250.72`) to current public control-plane defaults (`64.229.113.233`).

### Validation

- Verify config wiring:
  - `rg --line-number "with_compute_env\\.sh|worker-gpu]|autostart=true|TEMPORAL_ADDRESS|MINIO_ENDPOINT" scripts/supervisord.conf scripts/with_compute_env.sh onstart.sh`
- Verify shell syntax:
  - `bash -n scripts/with_compute_env.sh`
- Verify image build path still uses expected supervisor config:
  - `rg --line-number "COPY scripts/supervisord.conf /etc/supervisor/supervisord.conf" Dockerfile.base`

### Rollback

1. Revert `scripts/supervisord.conf` commands back to direct `uvicorn` / `python3 -m src.backend.worker` invocation.
2. Revert `worker-gpu` `autostart=true` to `autostart=false`.
3. Revert `onstart.sh` endpoint defaults to previous values.
4. Remove `scripts/with_compute_env.sh`.

## 2026-02-13 - Rotate Vast SSH Endpoint to `ssh3.vast.ai:15307` and Refresh Live Specs

- Objective: align compute-plane SSH access and spec records with the newly running Vast.ai instance.
- Root cause:
  - Previous endpoint values (`ssh2.vast.ai:27139`) were no longer reachable.
  - `raw_vast.json` still reflected older instance metadata (`ssh6.vast.ai:17293`, stale observed specs).
- Changes:
  - `.env`
    - Updated `VAST_HOST` to `ssh3.vast.ai`.
    - Updated `VAST_PORT` to `15307`.
  - `.env.example`
    - Updated `VAST_HOST` to `ssh3.vast.ai`.
    - Updated `VAST_PORT` to `15307`.
  - `docs/Perimeter.md`
    - Updated compute-plane host references from `ssh2.vast.ai` to `ssh3.vast.ai`.
    - Updated Norfolk tunnel command to:
      - `ssh -p 15307 root@ssh3.vast.ai -L 8080:localhost:8080`
  - `raw_vast.json`
    - Updated SSH endpoint fields (`ssh_host`, `ssh_port`).
    - Refreshed `spec_checked_at_utc`, `spec_check_method`, and `observed_specs` from live SSH checks.

### Validation

- Verify endpoint rotation in config/docs:
  - `rg --line-number "VAST_HOST=|VAST_PORT=|ssh3\.vast\.ai|15307" .env .env.example docs/Perimeter.md raw_vast.json`
- Verify SSH authentication:
  - `ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i ~/.ssh/id_huihuang2vastai -p 15307 root@ssh3.vast.ai "hostname; whoami"`
- Verify refreshed runtime specs:
  - `ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i ~/.ssh/id_huihuang2vastai -p 15307 root@ssh3.vast.ai "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; nproc; free -m | sed -n '2p'; df -BG / | tail -n 1; grep PRETTY_NAME /etc/os-release"`

### Rollback

1. Revert host/port values in `.env` and `.env.example` to the previous endpoint.
2. Revert compute-plane host and tunnel command lines in `docs/Perimeter.md`.
3. Restore previous SSH/spec fields in `raw_vast.json`.
4. Re-run SSH validation against the rolled-back endpoint.

## 2026-02-13 - Fix build-app Disk Exhaustion in BuildKit Snapshot Stage

- Objective: prevent `build-app` failures like `ResourceExhausted ... /var/lib/buildkit/... no space left on device` during app smoke image build.
- Root cause:
  - `build-app` used Buildx `docker-container` with `load: true`, which increases local snapshot/export pressure on constrained runner disks.
  - App job also configured `type=gha` cache directives, locking the job to buildkit-container behavior.
- Changes:
  - `.github/workflows/deploy.yml`
    - In `build-app` job `Set up Docker Buildx`, switched driver:
      - `docker-container -> docker`
    - Removed app-image GHA cache directives:
      - smoke build: removed `cache-from: type=gha,scope=app`
      - publish build: removed `cache-from/cache-to type=gha,scope=app`
    - Base-image jobs remain on `docker-container` with GHA cache unchanged.

### Validation

- Verify app Buildx driver and cache removal:
  - `rg --line-number "build-app:|Set up Docker Buildx|driver: docker|cache-from: type=gha,scope=app|cache-to: type=gha,scope=app" .github/workflows/deploy.yml`
- Re-run `Build and Push to GHCR` and confirm:
  - app smoke build no longer fails at `WORKDIR /workspace` with `ResourceExhausted`.
  - smoke + publish steps complete successfully.

### Rollback

1. In `.github/workflows/deploy.yml` `build-app` job, restore `driver: docker-container`.
2. Restore app `cache-from/cache-to type=gha,scope=app` lines in smoke/publish steps.
3. Re-run workflow and compare disk behavior.

## 2026-02-13 - Align CI Minimal GHCR Base Selection with Prebuilt Tags

- Objective: reduce unnecessary local base rebuilds in `CI Minimal Image Boot` and harden GHCR build-cache compatibility in deploy jobs.
- Root cause:
  - CI minimal flow probed only `ghcr.io/<repo>-base:latest`, while push-path base publishing now centers on `llama-prebuilt-*` tags.
  - Deploy jobs using `type=gha` cache depended on implicit Buildx driver defaults instead of explicit driver selection.
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Updated `Resolve base image strategy` to evaluate prebuilt candidates in order:
      - `llama-prebuilt-latest`
      - `latest`
      - `llama-src-latest`
    - Candidate is accepted only when pull + dependency probe pass; otherwise falls back to local base build.
  - `.github/workflows/deploy.yml`
    - Added explicit Buildx driver in GHCR jobs:
      - `driver: docker-container`
    - Kept `driver-opts: network=host` unchanged.

### Validation

- Verify CI minimal candidate order and fallback:
  - `rg --line-number "PREBUILT_CANDIDATES|llama-prebuilt-latest|llama-src-latest|No usable prebuilt GHCR base image found" .github/workflows/ci-minimal-image.yml`
- Verify deploy Buildx driver explicitness:
  - `rg --line-number "Set up Docker Buildx|driver: docker-container|driver-opts: network=host" .github/workflows/deploy.yml`
- Re-run workflows:
  - `CI Minimal Image Boot`
  - `Build and Push to GHCR`

### Rollback

1. In `.github/workflows/ci-minimal-image.yml`, revert prebuilt candidate loop to single-image probe (`...-base:latest`).
2. In `.github/workflows/deploy.yml`, remove `driver: docker-container` lines from Buildx setup steps.
3. Re-run both workflows and confirm behavior matches previous baseline.

## 2026-02-13 - Reduce build-app Disk Pressure on Runner

- Objective: avoid `No space left on device` failures during `build-app` on self-hosted runner.
- Root cause:
  - App pipeline performs smoke build + publish build in one job.
  - Residual Docker images/cache plus large cache/provenance export can exhaust root disk over long runs.
- Changes:
  - `.github/workflows/deploy.yml`
    - Enhanced `Reclaim disk space before app build`:
      - added `docker system df` visibility.
      - added `_diag` log cleanup (`/home/runner/actions-runner/cached/_diag`).
      - added extra prune (`docker image prune`, `docker volume prune`).
    - Added new step `Reclaim disk space before app publish build`:
      - removes `cres-smoke:<sha>` image and prunes builder/image/volume before final push build.
      - includes `_diag` log cleanup and disk usage print.
    - Reduced app publish build artifact pressure:
      - `cache-to` mode changed `max -> min`
      - disabled `provenance` and `sbom` for app publish step.

### Validation

- Verify new cleanup steps and prune calls:
  - `rg --line-number "Reclaim disk space before app build|Reclaim disk space before app publish build|docker system df|cached/_diag|docker image prune|docker volume prune|cres-smoke:\\$\\{\\{ github.sha \\}\\}" .github/workflows/deploy.yml`
- Verify app publish build output settings:
  - `rg --line-number "cache-to: type=gha,scope=app,mode=min|provenance: false|sbom: false" .github/workflows/deploy.yml`
- Re-run push-triggered workflow and confirm no `_diag` disk exhaustion in `build-app`.

### Rollback

1. Remove the additional publish-cleanup step.
2. Revert app cleanup step to previous prune subset.
3. Restore app publish `cache-to mode=max`, `provenance`, and `sbom` settings.

## 2026-02-13 - Stabilize Push Path by Building Prebuilt Base Every Push and Pinning SHA Tag

- Objective: prevent push-triggered `build-app` from resolving stale/invalid base tags.
- Root cause:
  - `build-base-llama-prebuilt` previously ran only when base-related files changed.
  - Push runs without base changes could skip prebuilt build and force app to reuse old tags (`latest`), causing import/runtime mismatches.
  - Dependency probe used default image entrypoint, which could fail for reasons unrelated to Python deps.
- Changes:
  - `.github/workflows/deploy.yml`
    - `build-base-llama-prebuilt` now runs on every `push` (manual prebuilt path unchanged).
    - `build-app` push path now prefers current-run prebuilt SHA tag:
      - `llama-prebuilt-<sha_short>`
    - Dependency probe now runs with:
      - `docker run --entrypoint python3 ...`
      - avoids entrypoint side-effects during import validation.

### Validation

- Verify prebuilt job trigger policy:
  - `rg --line-number "build-base-llama-prebuilt|github.event_name == 'push'" .github/workflows/deploy.yml`
- Verify push path app base pinning:
  - `rg --line-number "base_tag=\\\"llama-prebuilt-\\$\\{\\{ needs.filter.outputs.sha_short \\}\\}\\\"" .github/workflows/deploy.yml`
- Verify probe uses Python entrypoint override:
  - `rg --line-number \"--entrypoint python3\" .github/workflows/deploy.yml`

### Rollback

1. Restore old prebuilt job condition requiring base-file change on push.
2. Remove push-time SHA pinning and revert to prior base-tag selection.
3. Revert dependency probe command to previous invocation.

## 2026-02-13 - Reject Stale Base Tags Missing Runtime Dependencies in build-app

- Objective: prevent app smoke failures caused by selecting an existing but stale base image tag lacking Python runtime deps.
- Root cause:
  - `build-app` base selection previously checked only tag existence.
  - Fallback could pick `...-base:latest` even when it lacked required deps (`fastapi`, `uvicorn`, `httpx`, `temporalio`, `minio`, `yt_dlp`, `faster_whisper`, `torch`).
- Changes:
  - `.github/workflows/deploy.yml`
    - In `Select app base image route`, added `verify_base_runtime_deps()` probe using containerized Python imports.
    - Candidate base image is accepted only when:
      - metadata exists (`imagetools inspect`) and
      - dependency probe passes.
    - Keeps previous candidate fallback order but blocks stale images from being selected.

### Validation

- Verify probe function and gating logic exist:
  - `rg --line-number "verify_base_runtime_deps|base dependency probe failed|imagetools inspect .*verify_base_runtime_deps|fastapi|torch" .github/workflows/deploy.yml`
- Re-run push-triggered deploy workflow:
  - Expected:
    - `build-app` does not select base tags with missing imports.
    - `container_smoke.sh` import check no longer fails for missing core modules.

### Rollback

1. Remove `verify_base_runtime_deps()` from `Select app base image route`.
2. Restore existence-only selection condition in candidate loop.

## 2026-02-13 - Fix build-app Base Tag Bootstrap Failure on Push

- Objective: prevent `build-app` failure when `llama-prebuilt-latest` does not exist yet in GHCR.
- Root cause:
  - Push path defaulted app base to `...-base:llama-prebuilt-latest`.
  - When this tag was missing (first bootstrap / publish lag), app build failed before fallback.
- Changes:
  - `.github/workflows/deploy.yml`
    - Updated `Select app base image route`:
      - resolve candidate base tags by availability using `docker buildx imagetools inspect`.
      - push + prebuilt route candidate order:
        1) `llama-prebuilt-latest`
        2) `latest`
        3) `llama-src-latest`
      - manual route still prefers variant-specific `-<sha>` tag first, then falls back.
    - `APP_BASE_IMAGE` now always uses resolved existing image tag.

### Validation

- Verify fallback resolver exists in app route step:
  - `rg --line-number "candidates=\\(\\)|imagetools inspect|llama-prebuilt-latest|llama-src-latest|APP_BASE_IMAGE=\\$resolved" .github/workflows/deploy.yml`
- Re-run push-triggered deploy workflow:
  - Expected: `build-app` no longer fails with `llama-prebuilt-latest: not found`.

### Rollback

1. Revert resolver block in `Select app base image route`.
2. Restore previous fixed-tag assignment for `APP_BASE_IMAGE`.

## 2026-02-13 - Fix Dual-Route Failures (Runner Disk + Missing llama-src-latest)

- Objective: stabilize both routes after observed failures:
  - `minimal-build-and-boot`: runner disk exhaustion (`No space left on device` in `_diag`).
  - `llama-prebuilt` route: missing source artifact image (`llama-src-latest: not found`).
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Keep `workflow_dispatch` only to avoid push-triggered heavy builds that can exhaust runner disk.
  - `.github/workflows/deploy.yml`
    - In `build-base-llama-prebuilt`, added artifact-image resolver:
      - primary: `...-base:llama-src-latest`
      - fallback: `...-base:latest`
      - fail with explicit error if neither exists.
    - Build arg `LLAMA_ARTIFACT_IMAGE` now comes from resolver output.
  - `Dockerfile`
    - Default app base changed to:
      - `ghcr.io/jianshelu/cres_ytdlp-base:llama-prebuilt-latest`

### Validation

- Verify minimal workflow trigger scope:
  - `rg --line-number "^on:|workflow_dispatch:|push:|pull_request:" .github/workflows/ci-minimal-image.yml`
- Verify prebuilt artifact fallback logic:
  - `rg --line-number "Resolve llama artifact source image|llama-src-latest|base:latest|llama_artifact_image" .github/workflows/deploy.yml`
- Verify Docker default base route:
  - `rg --line-number "^ARG BASE_IMAGE=ghcr.io/jianshelu/cres_ytdlp-base:llama-prebuilt-latest" Dockerfile`

### Rollback

1. Revert resolver step in `.github/workflows/deploy.yml` and restore fixed `LLAMA_ARTIFACT_IMAGE=...:llama-src-latest`.
2. Revert `Dockerfile` base default to previous tag.
3. (Optional) restore push/pull_request triggers in `.github/workflows/ci-minimal-image.yml` if automatic minimal CI is required.

## 2026-02-13 - Split Trigger Policy by Base Route (Prebuilt Auto on Push, Source Compile Manual)

- Objective: enforce mixed trigger policy:
  - `llama-prebuilt` route: keep auto image build on `push`.
  - `llama-src` route (compile llama.cpp): manual `workflow_dispatch` only.
- Changes:
  - `.github/workflows/deploy.yml`
    - Added `push` trigger for main branch with image-relevant paths.
    - Restricted `build-base-llama-src` to:
      - `github.event_name == 'workflow_dispatch'`
      - `inputs.base_variant == 'llama-src'`
    - Restricted `build-base-llama-prebuilt` to:
      - push with base-impacting changes, or
      - manual run with `base_variant == 'llama-prebuilt'`
    - `llama-prebuilt` build now imports llama artifacts from:
      - `...-base:llama-src-latest`
    - App base selection now routes:
      - `push` -> `llama-prebuilt-latest`
      - `workflow_dispatch` -> `llama-src-<sha>` or `llama-prebuilt-<sha>` by input.

### Validation

- Verify triggers:
  - `rg --line-number "^on:|push:|workflow_dispatch:" .github/workflows/deploy.yml`
- Verify compile route is manual-only:
  - `rg --line-number "build-base-llama-src|inputs.base_variant == 'llama-src'|github.event_name == 'workflow_dispatch'" .github/workflows/deploy.yml`
- Verify prebuilt route supports push:
  - `rg --line-number "build-base-llama-prebuilt|github.event_name == 'push'|llama-src-latest" .github/workflows/deploy.yml`
- Verify app route selection:
  - `rg --line-number "variant=\"llama-prebuilt\"|base_tag=\"llama-prebuilt-latest\"|base_tag=\\\"\\$\\{variant\\}-\\$\\{\\{ needs.filter.outputs.sha_short \\}\\}\\\"" .github/workflows/deploy.yml`

### Rollback

1. Remove `push` trigger block from `.github/workflows/deploy.yml`.
2. Restore old job conditions where both base routes were manual-only.
3. Revert app base selection logic to fixed `:llama-src-latest` or previous behavior.

## 2026-02-13 - Make Compiled-Image Build Manual-Only and Disable Push-Triggered Image Builds

- Objective: ensure image build jobs (especially llama.cpp compile route) are manually triggered only, and stop push-triggered image build executions.
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Removed `push` trigger.
    - Removed `pull_request` trigger.
    - Kept `workflow_dispatch` only.
  - `.github/workflows/deploy.yml`
    - No trigger change needed (already `workflow_dispatch` only).

### Validation

- Verify manual-only trigger in CI minimal workflow:
  - `rg --line-number "^on:|workflow_dispatch:|push:|pull_request:" .github/workflows/ci-minimal-image.yml`
  - Expected: only `on:` and `workflow_dispatch:` appear.
- Verify deploy workflow is still manual-only:
  - `rg --line-number "^on:|workflow_dispatch:|push:|pull_request:" .github/workflows/deploy.yml`
  - Expected: only `on:` and `workflow_dispatch:` appear.

### Rollback

1. Restore removed `push` and `pull_request` blocks in `.github/workflows/ci-minimal-image.yml`.
2. Re-run a commit on `main` to confirm automatic workflow triggering resumes.

## 2026-02-13 - Dual Base Build Routes on Vast.ai Base (llama-src vs llama-prebuilt)

- Objective: provide two GHCR base-image routes with explicit tags:
  - `llama-src-*`: compile `llama.cpp` during build.
  - `llama-prebuilt-*`: do not compile; reuse llama artifacts from prebuilt image.
- Changes:
  - Added `Dockerfile.base.prebuilt`:
    - `FROM vastai/base-image:cuda-12.4.1-auto` as runtime base.
    - imports `/app/llama-server` and related libraries from `LLAMA_ARTIFACT_IMAGE`.
    - keeps runtime dependency installation aligned with `Dockerfile.base`.
  - Updated `.github/workflows/deploy.yml`:
    - Added `workflow_dispatch` input `base_variant` (`llama-src` / `llama-prebuilt`).
    - `build-base-llama-src` publishes:
      - `-base:llama-src-latest`
      - `-base:llama-src-<shortsha>`
      - backward-compatible `-base:latest` and `-base:<shortsha>`
    - Added `build-base-llama-prebuilt` publishing:
      - `-base:llama-prebuilt-latest`
      - `-base:llama-prebuilt-<shortsha>`
    - App build route now selects base tag via `base_variant`.
  - Updated `Dockerfile` default base image tag:
    - `ghcr.io/jianshelu/cres_ytdlp-base:llama-src-latest`

### Validation

- Verify new base Dockerfile exists:
  - `rg --line-number "Dockerfile.base.prebuilt|LLAMA_ARTIFACT_IMAGE|COPY --from=llama_artifacts /app/" Dockerfile.base.prebuilt`
- Verify deploy workflow has dual routes and tags:
  - `rg --line-number "build-base-llama-src|build-base-llama-prebuilt|llama-src-latest|llama-prebuilt-latest|base_variant" .github/workflows/deploy.yml`
- Verify app build uses selected base image:
  - `rg --line-number "APP_BASE_IMAGE|BASE_IMAGE=\\$\\{\\{ env.APP_BASE_IMAGE \\}\\}" .github/workflows/deploy.yml`
  - `rg --line-number "^ARG BASE_IMAGE=ghcr.io/jianshelu/cres_ytdlp-base:llama-src-latest" Dockerfile`

### Rollback

1. Remove `Dockerfile.base.prebuilt`.
2. Revert `.github/workflows/deploy.yml` to single `build-base` job and fixed `-base:latest` app base arg.
3. Revert `Dockerfile` base default tag to previous `-base:latest`.

## 2026-02-13 - Correct Torch Availability Assumption and Install from PyTorch cu124 Index

- Objective: fix base-image build failure where `python3 -c "import torch"` fails because `torch` is not present in runtime Python environment.
- Root cause:
  - `requirements.instance.txt` removed `torch` under the assumption that `vastai/base-image:cuda-12.4.1-auto` preinstalls it for `python3`.
  - In CI build context, `python3` environment used by `pip3` does not contain `torch`, causing hard failure at validation line.
- Changes:
  - `Dockerfile.base`
    - Added torch install args:
      - `TORCH_VERSION=2.6.0+cu124`
      - `TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124`
    - Updated Python dependency layer:
      - keep `pip3 install -r /tmp/requirements.instance.txt`
      - if `torch` import fails, install `torch==2.6.0+cu124` from PyTorch cu124 index
      - keep final `python3` import validation with version/cuda print.
  - `requirements.instance.txt`
    - Updated comment to reflect Dockerfile-managed torch install strategy.

### Validation

- Verify Dockerfile fallback install logic:
  - `rg --line-number "TORCH_VERSION|TORCH_INDEX_URL|if ! python3 -c \"import torch\"|torch==\\$\\{TORCH_VERSION\\}" Dockerfile.base`
- Verify requirements note:
  - `rg --line-number "torch is installed in Dockerfile.base|PyTorch cu124 index" requirements.instance.txt`
- Re-run base build:
  - `docker build --progress=plain -f Dockerfile.base .`
  - Expected:
    - no `ModuleNotFoundError: No module named 'torch'`
    - log contains `torch available: ... cuda: ...`

### Rollback

1. Remove `TORCH_VERSION` and `TORCH_INDEX_URL` args in `Dockerfile.base`.
2. Remove the conditional torch install block and restore previous validation flow.
3. Revert comments in `requirements.instance.txt` to previous wording.

## 2026-02-12 - Prevent Disk Exhaustion During Python Dependency Layer

- Objective: avoid `No space left on device` during base-image `pip install` while preserving GPU runtime compatibility.
- Root cause:
  - `requirements.instance.txt` attempted to install `torch`, triggering large CUDA dependency wheel downloads (e.g. `nvidia_cudnn_cu12` ~700MB) on top of existing build layers.
  - CI runner disk could exhaust in this layer before install completed.
- Changes:
  - `requirements.instance.txt`
    - Removed direct `torch` install line.
    - Added note that `torch` is expected from `vastai/base-image:cuda-12.4.1-auto`.
  - `Dockerfile.base`
    - Added explicit runtime validation after pip dependencies:
      - `python3 -c "import torch; ..."`
    - Build now fails fast if base image unexpectedly lacks `torch`, without downloading huge wheel stacks.

### Validation

- Verify `torch` is no longer in requirements:
  - `rg --line-number "^torch|torch is expected to be preinstalled" requirements.instance.txt`
- Verify Dockerfile checks torch availability:
  - `rg --line-number "import torch; print\\('torch preinstalled:'" Dockerfile.base`
- Re-run base build:
  - `docker build --progress=plain -f Dockerfile.base .`
  - Expected:
    - No large `nvidia_cudnn_cu12` wheel download in pip step.
    - `torch preinstalled: <version>` output appears.

### Rollback

1. Restore `torch` line in `requirements.instance.txt`.
2. Remove the `python3 -c "import torch; ..."` validation line from `Dockerfile.base`.
3. Re-run build and confirm old behavior.

## 2026-02-12 - Fix Non-Interactive Supervisor Install in Dockerfile.base

- Objective: prevent CI/docker build failure caused by interactive `dpkg` conffile prompt when installing `supervisor`.
- Root cause:
  - `vastai/base-image:cuda-12.4.1-auto` may already include `/etc/supervisor/supervisord.conf`.
  - `apt-get install supervisor` prompted for conffile conflict resolution; CI has no stdin, so `dpkg` exited with code `1`.
- Changes:
  - `Dockerfile.base`
    - Updated system dependency install step to force non-interactive conffile behavior:
      - `DEBIAN_FRONTEND=noninteractive`
      - `-o Dpkg::Options::="--force-confdef"`
      - `-o Dpkg::Options::="--force-confold"`
- Validation:
  - `rg --line-number "DEBIAN_FRONTEND=noninteractive|force-confdef|force-confold|supervisor" Dockerfile.base`
  - Re-run base build and confirm no prompt:
    - `docker build --progress=plain -f Dockerfile.base .`
- Rollback:
1. Revert the `DEBIAN_FRONTEND` and `Dpkg::Options` additions in `Dockerfile.base`.
2. Re-run build to confirm previous prompt behavior returns.

## 2026-02-12 - Fix CUDA Driver Stub Link for llama.cpp Build

- Objective: resolve `libcuda.so.1 not found` and `undefined reference to cuMem*` linker failures in `Dockerfile.base` llama.cpp build stage.
- Root cause:
  - CUDA driver API symbols are provided by `libcuda.so.1` (driver/runtime side), but CI build environment only has CUDA toolkit stubs.
  - Linker did not consistently resolve stub path during server/tool linking.
- Changes:
  - `Dockerfile.base`
    - Added CUDA stub prep before CMake configure:
      - ensure stub symlink `libcuda.so.1 -> libcuda.so` in known stub directories.
      - export `LIBRARY_PATH` and `LD_LIBRARY_PATH` with stub directories.
    - Added CMake linker flags:
      - `-DCMAKE_EXE_LINKER_FLAGS="${CUDA_STUB_FLAGS}"`
      - `-DCMAKE_SHARED_LINKER_FLAGS="${CUDA_STUB_FLAGS}"`
      - where `CUDA_STUB_FLAGS` includes `-Wl,-rpath-link,<stub_dir>` for discovered stub dirs.

### Validation

- Verify stub-link setup exists:
  - `rg --line-number "CUDA_STUB_FLAGS|libcuda\\.so\\.1|LIBRARY_PATH|CMAKE_EXE_LINKER_FLAGS|CMAKE_SHARED_LINKER_FLAGS" Dockerfile.base`
- Re-run base build:
  - `docker build --progress=plain -f Dockerfile.base .`
  - Expected: no linker errors for `libggml-cuda.so` unresolved `cuMem*`/`cuDevice*`.

### Rollback

1. Remove stub-symlink/linker-flag block from `Dockerfile.base`.
2. Revert CMake flag additions for `CMAKE_EXE_LINKER_FLAGS` and `CMAKE_SHARED_LINKER_FLAGS`.
3. Re-run build and confirm behavior returns to previous baseline.

## 2026-02-12 - Harden llama.cpp Build Step for CI Target Drift

- Objective: reduce `Dockerfile.base` build failures in `llama.cpp` compile stage (`exit code 2`) when upstream target layout changes.
- Root cause:
  - Build step relied on a single target command (`--target llama-server`) and fixed artifact paths under `build/bin`.
  - If upstream CMake target/path behavior changes, the step can fail even when source and toolchain are otherwise healthy.
- Changes:
  - `Dockerfile.base`
    - Changed `LLAMA_CPP_REF` default to empty so clone uses upstream default branch unless explicitly pinned.
    - Added fallback logic:
      - first try `cmake --build ... --target llama-server`
      - if that fails, retry with full `cmake --build ...` to tolerate target-name drift.
    - Switched artifact collection to dynamic discovery:
      - find `llama-server` binary in `build/`
      - find/copy `libllama.so*` and `libggml*.so*` wherever generated.

### Validation

- Verify fallback logic exists:
  - `rg --line-number "llama-server target build failed, retrying with full build|--target llama-server|cmake --build build --config Release -j" Dockerfile.base`
- Verify dynamic artifact copy exists:
  - `rg --line-number "find /opt/llama.cpp/build -type f -name llama-server|find /opt/llama.cpp/build -type f -name 'libllama.so\\*'|find /opt/llama.cpp/build -type f -name 'libggml\\*.so\\*'" Dockerfile.base`
- Re-run CI base build:
  - expected: no immediate failure at `Dockerfile.base` line 16 due target/path mismatch.

### Rollback

1. Revert `Dockerfile.base` build step to single target build and fixed `build/bin` copy paths.
2. Re-run CI and confirm previous behavior.

## 2026-02-12 - Fix Invalid Vast.ai Base Image Reference Format

- Objective: make base image build parse correctly by replacing invalid `FROM` reference with a valid, pullable Vast.ai CUDA tag.
- Root cause:
  - `FROM vastai/base-image:@vastai-automatic-tag` is not a valid Docker image reference format.
  - Docker/buildx fails early with `invalid reference format`.
- Changes:
  - `Dockerfile.base`
    - Replaced runtime base with:
      - `FROM vastai/base-image:cuda-12.4.1-auto`
  - `.github/workflows/ci-minimal-image.yml`
    - Updated base-image verification grep to match the new valid tag.

### Validation

- Validate base reference:
  - `rg --line-number "^FROM vastai/base-image:cuda-12.4.1-auto" Dockerfile.base`
- Validate CI check matches:
  - `rg --line-number "FROM vastai/base-image:cuda-12.4.1-auto" .github/workflows/ci-minimal-image.yml`
- Run build parse check:
  - `docker build -f Dockerfile.base .`
  - Expected: no `invalid reference format` error at `FROM`.

### Rollback

1. Revert `Dockerfile.base` and `ci-minimal-image.yml` to previous base reference.
2. Re-run build to confirm prior behavior is restored.

## 2026-02-12 - Source-of-Truth Order Alignment (AGENTS.md)

- Objective: align planning and task governance with `AGENTS.md` `Where the truth lives vividly`.
- Root cause:
  - `AGENTS.md` introduced explicit source precedence and later renamed the section to `Where the truth lives vividly`.
  - `docs/PLAN.md` and `docs/Task.md` needed wording alignment plus explicit vivid marker examples for human-computer interaction.
  - `AGENTS.md` now explicitly requires `PLAN.md` and `Task.md` to conform to the vivid formatting standard and be updated when inconsistent.
- Changes:
  - `docs/PLAN.md`
    - Added this governance entry to formalize source precedence:
      - `.agents/skills/cres-triage/SKILL.md` (authoritative)
      - `docs/PLAN.md` (current status)
      - `docs/Task.md` (task execution list)
      - `docs/DECISIONS.md` (optional tradeoffs)
    - Preserved existing source-of-truth hierarchy content while aligning wording to `Where the truth lives vividly`.
    - Added `Where the truth lives vividly` formatting note for updates:
      - `&#128994;&#128736; Skills` -> `.agents/skills/cres-triage/SKILL.md` (Rule Source)
      - `&#128309;&#128214; Plan` -> `docs/PLAN.md` (Live Progress)
      - `&#128992;&#128450; Task List` -> `docs/Task.md` (Actionable Items)
      - `&#128995;&#9888; Decisions` -> `docs/DECISIONS.md` (Tradeoff Records)
      - use color+emoji markers in update summaries (`&#128309;` files, `&#128994;` validation, `&#128992;` rollback).
      - keep vivid content scoped to human-computer interaction documentation only.
      - keep `PLAN.md` and `Task.md` formatting consistent with the vivid standard and update mismatches.
  - `docs/Task.md`
    - Updated today's `Docs & Ops` tasks to mark source-of-truth, vivid-format conformance, and consistency checks complete.

### Validation

- Verify `PLAN.md` contains this alignment entry:
  - `rg --line-number "Source-of-Truth Order Alignment|Where the truth lives vividly|vivid formatting standard|updated when inconsistent|cres-triage/SKILL\.md|docs/Task\.md|docs/DECISIONS\.md|Rule Source|Live Progress|Actionable Items|Tradeoff Records" docs/PLAN.md`
- Verify `Task.md` includes today's completed alignment tasks:
  - `rg --line-number "Where the truth lives vividly|Update daily task tracking source references|vivid color\\+emoji interaction requirement|vivid formatting standard" docs/Task.md`

### Rollback

1. Remove this `Source-of-Truth Order Alignment (AGENTS.md)` section from `docs/PLAN.md`.
2. Remove the four alignment task lines from `docs/Task.md` under `2026-02-12 (Thursday) -> Docs & Ops`.
3. Re-run the validation `rg` commands and confirm no alignment-entry matches remain.

## 2026-02-12 - CI Prebuilt Base Dependency Probe Before Reuse

- Objective: prevent smoke failures where app container lacks Python runtime deps after reusing stale GHCR base image.
- Root cause:
  - `ci-minimal-image.yml` reused `ghcr.io/<repo>-base:latest` when pull succeeded, but did not validate dependency completeness.
  - A stale/outdated GHCR base could be pullable yet missing `requirements.instance.txt` packages, leading to smoke import failures (`fastapi`, `temporalio`, `torch`, etc.).
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - In `Resolve base image strategy`, added `verify_base_runtime_deps()` probe:
      - Runs `python3` import checks inside pulled prebuilt base image.
      - Validates:
        - `fastapi`, `uvicorn`, `httpx`, `temporalio`, `minio`, `yt_dlp`, `faster_whisper`, `torch`.
    - Reuse policy now becomes:
      - Pull success + dependency probe pass -> reuse GHCR base.
      - Pull success + dependency probe fail -> fallback local base build.
      - Pull fail -> fallback local base build.

### Validation

- Verify probe exists:
  - `rg --line-number "verify_base_runtime_deps|prebuilt base dependency probe|faster_whisper|yt_dlp|torch" .github/workflows/ci-minimal-image.yml`
- Re-run `CI Minimal Image Boot` with no base file changes:
  - If GHCR base is stale: logs show probe failure and `build_local=true`.
  - If GHCR base is valid: logs show probe pass and reuse path.
- Confirm smoke no longer fails with missing imports in `scripts/container_smoke.sh`.

### Rollback

1. Remove `verify_base_runtime_deps()` function and probe branch from `Resolve base image strategy`.
2. Restore original reuse rule (pull success -> reuse directly).
3. Re-run CI workflow to confirm old behavior.

## 2026-02-12 - Fix CI Base/App Build Cache Backend Mismatch (docker driver)

- Objective: stop `CI Minimal Image Boot` failures caused by Buildx cache backend incompatibility.
- Root cause:
  - Workflow uses Buildx `driver: docker` to ensure local image reuse (`cres-base-ci:<sha>` -> app build arg).
  - Same workflow also configured `cache-from/cache-to: type=gha`, which is unsupported by `docker` driver in current runner configuration.
  - Failure surfaced as:
    - `ERROR: failed to build: Cache export is not supported for the docker driver.`
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Removed `cache-from: type=gha,scope=base-ci` and `cache-to: type=gha,scope=base-ci,mode=max` from local base build step.
    - Removed `cache-from: type=gha,scope=app-ci` and `cache-to: type=gha,scope=app-ci,mode=max` from local app build step.
    - Kept `driver: docker` unchanged to preserve local base-image reuse behavior.

### Validation

- Verify cache lines are absent in CI minimal workflow:
  - `rg --line-number "cache-from: type=gha,scope=(base-ci|app-ci)|cache-to: type=gha,scope=(base-ci|app-ci)" .github/workflows/ci-minimal-image.yml`
  - Expected: no matches.
- Re-run `CI Minimal Image Boot`:
  - Confirm no `Cache export is not supported for the docker driver` error.
  - Confirm app build still resolves `BASE_IMAGE=cres-base-ci:<sha>` successfully.

### Rollback

1. Re-add removed `cache-from/cache-to type=gha` lines in `.github/workflows/ci-minimal-image.yml`.
2. If cache is required, switch Buildx to a compatible driver/config (for example `docker-container` + cache backend support).
3. Re-run CI and verify base/app build path behavior.

## 2026-02-12 - GHCR Base Build Guardrails for llama.cpp Source Compile

- Objective: keep `llama.cpp` compiled in-image while reducing GHCR build failures caused by runner disk pressure and compile resource spikes.
- Root cause:
  - Source compile in `Dockerfile.base` increased build-time CPU/memory/disk demand.
  - GHCR workflow `deploy.yml` lacked explicit pre-build disk reclamation.
  - Base cache export used aggressive `mode=max`, increasing cache upload volume and failure surface.
- Changes:
  - `Dockerfile.base`
    - Added compile guard args:
      - `LLAMA_BUILD_JOBS=2` (default low parallelism)
      - `LLAMA_CUDA_ARCH=86` (target RTX 3060 class runtime)
    - Kept `llama.cpp` source compile with CUDA and limited artifacts copied to runtime:
      - `/app/llama-server`
      - `libllama.so*`
      - `libggml*.so*`
    - Added `strip --strip-unneeded` to reduce runtime artifact size.
  - `.github/workflows/deploy.yml`
    - Added base-impacting filters for `scripts/supervisord.conf` and `scripts/start-llama.sh`.
    - Added pre-build disk reclamation steps in both `build-base` and `build-app` jobs.
    - Passed base build args:
      - `LLAMA_BUILD_JOBS=2`
      - `LLAMA_CUDA_ARCH=86`
    - Reduced base cache export pressure:
      - `cache-to: type=gha,scope=base,mode=min`

### Validation

- Verify compile guard args and reduced runtime copy:
  - `rg --line-number "ARG LLAMA_CUDA_ARCH|ARG LLAMA_BUILD_JOBS|CMAKE_CUDA_ARCHITECTURES|llama-artifacts|libggml\\*|libllama\\.so\\*" Dockerfile.base`
- Verify GHCR workflow has disk reclaim + build args:
  - `rg --line-number "Reclaim disk space before base build|Reclaim disk space before app build|LLAMA_BUILD_JOBS=2|LLAMA_CUDA_ARCH=86|cache-to: type=gha,scope=base,mode=min" .github/workflows/deploy.yml`
- Trigger `Build and Push to GHCR` and confirm:
  - Base build starts with disk before/after logs.
  - No `No space left on device` during base build.
  - Base image push succeeds with `llama-server` still present at runtime.

### Rollback

1. Revert `Dockerfile.base` compile guard args and artifact-copy narrowing.
2. Revert `deploy.yml` disk reclaim steps and base build args.
3. Restore base cache export to `mode=max` if desired.
4. Re-run GHCR workflow and compare baseline behavior.

## 2026-02-12 - Switch Runtime Base to Vast.ai Auto CUDA Image Tag (Keep llama.cpp Source Build)

- Objective: improve Vast.ai-side image pull/load performance by using `vastai/base-image:@vastai-automatic-tag` as runtime base while preserving `llama-server` via in-image `llama.cpp` source build.
- Root cause:
  - Runtime base used `ghcr.io/ggml-org/llama.cpp:server-cuda` directly, which may not benefit from Vast.ai-side base caching behavior.
  - Previous change only copied prebuilt `llama-server`; it did not keep source-compilation flow in `Dockerfile.base`.
- Changes:
  - `Dockerfile.base`
    - Switched runtime base to `FROM vastai/base-image:@vastai-automatic-tag`.
    - Added `llama_cpp_builder` stage (`nvidia/cuda:12.4.1-devel-ubuntu22.04`) to build `llama.cpp` from source with `GGML_CUDA=ON`.
    - Copied compiled artifacts from `/opt/llama.cpp/build/bin/` into `/app/` and linked `/usr/local/bin/llama-server`.
  - `.github/workflows/ci-minimal-image.yml`
    - Added positive verification for both:
      - `FROM vastai/base-image:@vastai-automatic-tag`
      - presence of `llama_cpp_builder` stage and `cmake --build ... --target llama-server` line.

### Validation

- Verify runtime base image line:
  - `rg --line-number "^FROM vastai/base-image:@vastai-automatic-tag" Dockerfile.base`
- Verify llama source compile stage exists:
  - `rg --line-number "^FROM nvidia/cuda:.* AS llama_cpp_builder|cmake --build build --config Release --target llama-server" Dockerfile.base`
- Verify CI check enforces base + compile stage:
  - `rg --line-number "Verify Vast.ai base and llama.cpp source build are configured|FROM vastai/base-image:@vastai-automatic-tag|llama_cpp_builder|cmake --build build --config Release --target llama-server" .github/workflows/ci-minimal-image.yml`

### Rollback

1. Revert `Dockerfile.base` to single-stage `FROM ghcr.io/ggml-org/llama.cpp:server-cuda`.
2. Remove `llama_cpp_builder` stage and `/app` copy/link lines.
3. Revert `.github/workflows/ci-minimal-image.yml` verification step accordingly.
4. Re-run CI to confirm previous behavior.

## 2026-02-12 - CI Minimal Build-and-Boot Base Reuse Optimization

- Objective: reduce unnecessary rebuild cost in `minimal-build-and-boot` while keeping deterministic smoke coverage.
- Root cause:
  - `CI Minimal Image Boot` always rebuilt `Dockerfile.base` locally, even when base-impacting files were unchanged.
  - Base image strategy lacked a deterministic reuse-or-rebuild decision.
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Added base-impacting change filter (`Dockerfile.base`, `requirements.instance.txt`, `scripts/supervisord.conf`, `scripts/start-llama.sh`).
    - Added conditional strategy:
      - Reuse GHCR base image (`ghcr.io/<repo>-base:latest`) when base files are unchanged.
      - Fallback to local base build when base files changed or pull fails.
    - Added GHA cache scopes for base/app CI builds (`base-ci`, `app-ci`).
    - Added `scripts/start-llama.sh` to workflow path triggers.

### Validation

- Verify new strategy steps exist:
  - `rg --line-number "Detect base-image affecting changes|Resolve base image strategy|Build base image \\(local, when required\\)" .github/workflows/ci-minimal-image.yml`
- Re-run `CI Minimal Image Boot`:
  - If base files unchanged: logs show GHCR base pull/tag path.
  - If base files changed: logs show local base build path.

### Rollback

1. Revert `.github/workflows/ci-minimal-image.yml` strategy/filter/guard additions.
2. Restore unconditional local base build in `minimal-build-and-boot`.
3. Re-run CI to confirm previous behavior.

## 2026-02-12 - CI Minimal Boot Disk-Pressure Guardrails

- Objective: prevent `minimal-build-and-boot` from failing with `No space left on device` on persistent/self-hosted runners.
- Root cause:
  - The workflow only removed runtime containers/network at the end.
  - Docker layers/build cache and old runner `_diag` logs could accumulate across runs and exhaust disk.
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Added pre-build reclaim step to print disk usage, trim old runner `_diag` logs, and run Docker prune commands.
    - Extended final cleanup to remove CI-tagged images and prune builder/volumes under `if: always()`.

### Validation

- Re-run `CI Minimal Image Boot` and confirm `Reclaim disk space before build` prints disk usage before/after cleanup.
- Confirm `minimal-build-and-boot` completes without `System.IO.IOException: No space left on device`.

### Rollback

1. Revert `.github/workflows/ci-minimal-image.yml` cleanup additions.
2. Re-run CI and confirm workflow behavior returns to previous baseline.

## 2026-02-12 - CI Smoke Queue Check Respects No-GPU Environments

- Objective: stop CI smoke failures where `worker-gpu` cannot start on non-GPU runners but queue registration still hard-requires `video-processing@gpu`.
- Root cause:
  - `scripts/container_smoke.sh` always tried to start `worker-gpu` and always validated both `@cpu` and `@gpu` queues.
  - On CI runners without CUDA, `worker-gpu` exits with spawn error by design, so hard-checking `@gpu` produced false negatives.
- Changes:
  - `scripts/container_smoke.sh`
    - Added `SMOKE_REQUIRE_GPU_QUEUE` policy (`auto|true|false`, default `auto`).
    - Auto mode detects CUDA availability via `torch.cuda.is_available()` and sets `SMOKE_EXPECT_GPU_QUEUE`.
    - Skips `worker-gpu` start when GPU is not expected.
    - Queue registration check now validates `@gpu` only when `SMOKE_EXPECT_GPU_QUEUE=1`.

### Validation

- Syntax:
  - `bash -n scripts/container_smoke.sh`
- Runtime behavior (CI no-GPU expected):
  - logs show `gpu queue expectation: 0`
  - `worker-gpu` start is skipped
  - queue check targets only `video-processing@cpu`

### Rollback

1. Revert `scripts/container_smoke.sh` to previous behavior.
2. Re-run CI and ensure both `@cpu` and `@gpu` are required again.

## 2026-02-12 - Transcriptions Hot-Path Optimization (AI programming / limit=30)

- Objective: eliminate repeated high-latency rendering on `/transcriptions` for large result sets by removing redundant recomputation in FastAPI hot path.
- Root cause:
  - `/api/transcriptions` cache validation rejected valid cached payloads when `combined_video_url` was empty, causing repeated full recomputation.
  - Transcript fetch path created new HTTP clients repeatedly under large fan-out, adding unnecessary connection overhead.
  - No in-process hot cache fallback existed when external cache miss/write happened.
- Changes:
  - `src/api/routers/transcriptions.py`
    - Added shared `httpx.AsyncClient` + bounded concurrency (`TRANSCRIPT_FETCH_CONCURRENCY`) for transcript payload fan-out.
    - Added configurable transcript fetch timeout (`TRANSCRIPT_FETCH_TIMEOUT_SECONDS`).
    - Removed strict cache rejection rule on empty `combined_video_url`; now cached response is accepted if schema-valid.
    - Added in-process memory cache with TTL/size bounds:
      - `TRANSCRIPTIONS_MEMORY_CACHE_TTL_SECONDS`
      - `TRANSCRIPTIONS_MEMORY_CACHE_MAX_ITEMS`
    - Added two-level cache order: memory cache -> MinIO cache -> recompute -> backfill both caches.
  - Runtime operation on huihuang:
    - Restarted FastAPI process to load updated hot-path code.

### Validation

- Syntax check:
  - `python -m compileall src/api/routers/transcriptions.py`
- API performance check (`AI programming`, `limit=30`):
  - `curl http://127.0.0.1:8000/api/transcriptions?query=AI%20programming&limit=30`
  - Observed:
    - run1: `ttfb ~3.14s`, `cache=miss`
    - run2/run3: `ttfb ~0.01s`, `cache=hit`
- Page check:
  - `curl http://127.0.0.1:3000/transcriptions?query=AI%20programming&limit=30`
  - Observed after warm cache: `ttfb ~0.02s`.

### Rollback

1. Revert router changes:
   - `git checkout -- src/api/routers/transcriptions.py`
2. Restart FastAPI service on huihuang.
3. Re-run the same curl checks to confirm behavior returns to previous baseline.

## 2026-02-12 - Archive Legacy Code-Sync Deploy Scripts and Enforce Immutable Instance Flow

- Objective: retire legacy instance code-sync deployment scripts, clarify `docker run` ownership, and enforce one-way code flow (`huihuang/GitHub -> GHCR -> instance`).
- Root cause:
  - `deploy_vast.sh` / `deploy_vast.py` still performed code sync and remote runtime mutation in `/workspace`.
  - `docker run` ownership was not explicitly documented, causing deployment boundary confusion.
- Changes:
  - `deploy_vast.sh`
    - Replaced with hard deprecation stub (exit 1).
  - `deploy_vast.py`
    - Replaced with hard deprecation stub (exit 1).
  - `scripts/archive/legacy_deploy_vast.sh`
    - Archived original legacy sync/deploy script.
  - `scripts/archive/legacy_deploy_vast.py`
    - Archived original legacy sync/deploy script.
  - `start_remote.sh`
    - Removed obsolete normalization reference to `deploy_vast.sh`.
  - `docs/vast_deployment.md`
    - Rewritten to define immutable deployment model, explicit `docker run` ownership (Vast runtime vs CI smoke), and manual incident runbook without instance code edits.

### Validation

- Verify legacy scripts are archived and stubs exist:
  - `Test-Path scripts/archive/legacy_deploy_vast.sh`
  - `Test-Path scripts/archive/legacy_deploy_vast.py`
  - `bash ./deploy_vast.sh` returns deprecation + non-zero.
  - `python ./deploy_vast.py` returns deprecation + non-zero.
- Verify startup script no longer references archived deploy script:
  - `rg --line-number "deploy_vast\.sh" start_remote.sh`
- Verify docs state `docker run` ownership and immutable flow:
  - `rg --line-number "Where `docker run` Actually Happens|immutable|Single-Flow Incident Handling" docs/vast_deployment.md`

### Rollback

1. Restore `deploy_vast.sh` and `deploy_vast.py` from `scripts/archive/legacy_deploy_vast.sh` and `scripts/archive/legacy_deploy_vast.py`.
2. Re-add `deploy_vast.sh` reference in `start_remote.sh` normalization line if needed.
3. Revert `docs/vast_deployment.md` to previous deployment-script-based runbook.
4. Re-validate operational startup path.
## 2026-02-12 - GPU Worker Recovery on ssh2 and Remote Runtime Bootstrap

- Objective: restore `video-processing@gpu` polling on Vast.ai (`ssh2.vast.ai:27139`) and clear `No worker available` on GPU queue.
- Root cause:
  - Remote instance had models only, but no project code and no Python runtime deps (`torch`, `temporalio`, `faster-whisper`, etc.).
  - Local `.env` pointed to a non-existent SSH key path, blocking operational SSH actions.
  - CPU-only worker import path required `torch` at module import time, causing CPU worker startup failure when `torch` is absent.
- Changes:
  - `.env`
    - Updated `VAST_SSH_KEY` to `~/.ssh/id_huihuang2vastai`.
  - `src/backend/activities.py`
    - Hardened temp cleanup behavior to avoid deleting active transfer artifacts:
      - Added minimum-age guard for cleanup candidates.
      - Stopped cleanup of `.part` / `.part.minio` files.
  - Remote runtime operations (ssh2 instance):
    - Synced repo to `/workspace/cres_ytdlp_norfolk`.
    - Installed runtime dependencies via `requirements.instance.txt`.
    - Started GPU worker with enforced queue/env:
      - `WORKER_MODE=gpu`
      - `BASE_TASK_QUEUE=video-processing`
      - `TEMPORAL_ADDRESS=64.229.113.233:7233`
      - `MINIO_ENDPOINT=64.229.113.233:9000`

### Validation

- Verify CPU queue poller:
  - `temporal.exe task-queue describe --task-queue video-processing@cpu --task-queue-type workflow --address 127.0.0.1:7233`
  - Expected poller identity includes `huihuang@cpu`.
- Verify GPU queue poller:
  - `temporal.exe task-queue describe --task-queue video-processing@gpu --task-queue-type activity --address 64.229.113.233:7233`
  - Expected poller identity includes `<remote-host>@gpu` (observed: `ccf57720e953@gpu`).
- Verify remote worker process exists:
  - `ssh ... "ps -ef | grep backend.worker | grep -v grep"`

### Rollback

1. Revert `.env` SSH key path change if key management policy requires previous path.
2. Revert `src/backend/activities.py` temp cleanup adjustments.
3. Stop remote GPU worker:
   - `ssh ... "pkill -f src.backend.worker"`
4. Re-run queue describe commands to confirm `@gpu` poller is removed.

## 2026-02-12 - GHCR Base Image Pre-bakes Instance Python Dependencies

- Objective: ensure `requirements.instance.txt` dependencies are baked directly into GHCR build artifacts and avoid duplicate install during app image build.
- Root cause:
  - Instance runtime dependencies were installed in `Dockerfile` (app stage), not in `Dockerfile.base`.
  - `deploy.yml` base rebuild filter did not watch `requirements.instance.txt`.
- Changes:
  - `Dockerfile.base`
    - Added `COPY requirements.instance.txt /tmp/requirements.instance.txt`.
    - Added `pip3 install -r /tmp/requirements.instance.txt` and cache cleanup.
  - `Dockerfile`
    - Removed duplicate `requirements.instance.txt` installation layer.
    - Kept app image inheriting Python deps from `BASE_IMAGE`.
  - `.github/workflows/deploy.yml`
    - Added `requirements.instance.txt` to `filter.base` paths so base image rebuild triggers on dependency changes.

### Validation

- Verify base image build path includes dependency file:
  - `rg --line-number "requirements.instance.txt" Dockerfile.base .github/workflows/deploy.yml`
- Verify app Dockerfile no longer installs Python deps:
  - `rg --line-number "pip3 install|requirements.instance.txt" Dockerfile`
- Run GHCR workflow and confirm order:
  - `build-base` runs when `requirements.instance.txt` changes.
  - `build-app` uses `BASE_IMAGE=ghcr.io/<repo>-base:latest` and passes smoke.

### Rollback

1. Revert dependency installation block in `Dockerfile.base`.
2. Restore `requirements.instance.txt` install block in `Dockerfile`.
3. Remove `requirements.instance.txt` from `.github/workflows/deploy.yml` `filter.base`.
4. Re-run GHCR workflow to confirm old build behavior.

## 2026-02-12 - Control Plane Boot Unification and CPU Worker Availability

- Objective: eliminate boot-time startup drift and restore `video-processing@cpu` polling reliability on huihuang.
- Root cause:
  - CPU worker failed at import time because `src/backend/worker.py` imported `torch` unconditionally.
  - Existing scheduled tasks referenced missing launcher files (`C:\Users\rama\run_*.cmd`), so startup automation silently failed.
- Changes:
  - `src/backend/worker.py`
    - Switched `torch` import to lazy/conditional behavior.
    - `WORKER_MODE=cpu` now starts without requiring `torch`.
    - `WORKER_MODE=gpu` still enforces CUDA/torch prerequisites.
  - `scripts/start_control_plane_boot.ps1`
    - Added idempotent startup checks for Temporal (`7233`), MinIO (`9000`), FastAPI (`8000`).
    - Added idempotent CPU worker startup (`src.backend.worker`) with `.env`-derived settings.
    - Added readiness waits and startup logging under `.tmp/control-plane/`.
  - Task Scheduler (runtime ops)
    - Registered/used unified boot task: `CRES-ControlPlane-Boot`.
    - Disabled stale split tasks: `CRES-Temporal-8233`, `CRES-MinIO-9000`, `CRES-FastAPI-8000`.

### Validation

- Verify unified boot script exits cleanly:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_control_plane_boot.ps1`
- Verify listeners:
  - `7233` (Temporal), `9000` (MinIO), `8000` (FastAPI)
- Verify CPU worker process exists:
  - command line contains `-m src.backend.worker`
- Verify Temporal pollers for CPU queue:
  - `temporal.exe task-queue describe --task-queue video-processing@cpu --task-queue-type workflow --address 127.0.0.1:7233`
  - `temporal.exe task-queue describe --task-queue video-processing@cpu --task-queue-type activity --address 127.0.0.1:7233`
- Verify scheduler task result:
  - `Get-ScheduledTaskInfo -TaskName CRES-ControlPlane-Boot` returns `LastTaskResult : 0`

### Rollback

1. Revert `src/backend/worker.py` lazy torch import changes.
2. Revert `scripts/start_control_plane_boot.ps1` worker startup additions.
3. Disable `CRES-ControlPlane-Boot` and re-enable legacy tasks:
   - `CRES-Temporal-8233`
   - `CRES-MinIO-9000`
   - `CRES-FastAPI-8000`
4. Restart services manually and re-check queue pollers.

## 2026-02-12 - Vast Instance SSH Endpoint Rotation (ssh2)

- Objective: move instance access to the more stable Vast.ai endpoint provided by operations.
- Changes:
  - `.env`
    - Updated `VAST_HOST` to `ssh2.vast.ai`.
    - Updated `VAST_PORT` to `27139`.
  - `.env.example`
    - Updated `VAST_HOST` to `ssh2.vast.ai`.
    - Updated `VAST_PORT` to `27139`.
  - `docs/Perimeter.md`
    - Updated compute-plane host references from `ssh7.vast.ai` to `ssh2.vast.ai`.
    - Updated Norfolk tunnel command to:
      - `ssh -p 27139 root@ssh2.vast.ai -L 8080:localhost:8080`

### Validation

- Verify no stale host/port references remain in active docs/config:
  - `rg --line-number "ssh7\.vast\.ai|26311" docs/Perimeter.md .env .env.example`
- Verify SSH tunnel connectivity:
  - `ssh -p 27139 root@ssh2.vast.ai -L 8080:localhost:8080`

### Rollback

1. Revert host/port values in `.env` and `.env.example` to prior instance values.
2. Revert compute-plane host and tunnel command lines in `docs/Perimeter.md`.
3. Re-run the validation grep and SSH tunnel command.

## 2026-02-12 - Vast Instance SSH Endpoint Rotation

- Objective: align active SSH tunnel configuration and runbook entries with the new Vast.ai instance endpoint.
- Changes:
  - `.env`
    - Updated `VAST_HOST` to `ssh7.vast.ai`.
    - Updated `VAST_PORT` to `26311`.
  - `.env.example`
    - Updated `VAST_HOST` to `ssh7.vast.ai`.
    - Updated `VAST_PORT` to `26311`.
  - `docs/Perimeter.md`
    - Updated compute-plane host references from `ssh5.vast.ai` to `ssh7.vast.ai`.
    - Updated Norfolk tunnel command to:
      - `ssh -p 26311 root@ssh7.vast.ai -L 8080:localhost:8080`

### Validation

- Verify no stale host/port references remain in active docs/config:
  - `rg --line-number "ssh5\.vast\.ai|11319|ssh6\.vast\.ai|17293" docs/Perimeter.md .env .env.example`
- Verify SSH tunnel connectivity:
  - `ssh -p 26311 root@ssh7.vast.ai -L 8080:localhost:8080`

### Rollback

1. Revert host/port values in `.env` and `.env.example` to previous instance values.
2. Revert compute-plane host and tunnel command lines in `docs/Perimeter.md`.
3. Re-run the validation grep and SSH tunnel command.

## 2026-02-12 - CI Smoke IP Readiness Guard

- Objective: prevent empty smoke endpoint env values (e.g. `TEMPORAL_SMOKE_ADDR=:7233`) caused by transient container network/IP readiness race.
- Root cause: workflow resolved dependency IP immediately after `docker run`; Temporal occasionally returned empty IP, propagating an invalid endpoint into app container env.
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Added retry loops (up to 60s) for:
      - `temporal-ci` IP on `cres-ci`
      - `minio-ci` IP on `cres-ci`
    - Added explicit guard: fail step with diagnostics (`docker ps -a`, `docker inspect`) if IP remains empty.
  - `.github/workflows/deploy.yml`
    - Applied same readiness guard for:
      - `temporal-smoke` / `minio-smoke` on `cres-smoke`

### Validation

- Re-run workflows:
  - `CI Minimal Image Boot`
  - `Build and Push to GHCR` (smoke stage)
- Confirm env values in run logs are non-empty:
  - `TEMPORAL_SMOKE_ADDR=<ip>:7233`
  - `MINIO_SMOKE_ENDPOINT=<ip>:9000`
- Confirm smoke passes queue registration and no `invalid target URL: empty host`.

### Rollback

1. Revert retry/guard blocks in:
   - `.github/workflows/ci-minimal-image.yml`
   - `.github/workflows/deploy.yml`
2. Restore immediate IP resolution behavior.
3. Re-run workflows to confirm previous behavior.

## 2026-02-12 - CI Smoke Endpoint Resolution Hardening

- Objective: remove Docker DNS flakiness from CI smoke tests where `app-ci` intermittently fails to resolve `temporal-ci`/`temporal-smoke`.
- Root cause: `TEMPORAL_ADDRESS=temporal-ci:7233` (or `temporal-smoke`) depended on runtime container DNS resolution; failures surfaced as temporary name-resolution errors in queue registration checks.
- Changes:
  - `.github/workflows/ci-minimal-image.yml`
    - Resolve `temporal-ci` and `minio-ci` IPs via `docker inspect`.
    - Export:
      - `TEMPORAL_SMOKE_ADDR=<temporal_ip>:7233`
      - `MINIO_SMOKE_ENDPOINT=<minio_ip>:9000`
    - Start `app-ci` with those explicit endpoints.
  - `.github/workflows/deploy.yml`
    - Apply the same IP-resolution pattern for `temporal-smoke` / `minio-smoke`.
    - Start `app-smoke` with explicit endpoint env values.

### Validation

- Re-run:
  - `CI Minimal Image Boot`
  - `Build and Push to GHCR` (smoke section)
- Confirm smoke output no longer fails with:
  - `Temporary failure in name resolution` for Temporal address.
- Confirm queue registration reaches:
  - `queue registration ok`

### Rollback

1. Revert `.github/workflows/ci-minimal-image.yml` and `.github/workflows/deploy.yml` smoke endpoint changes.
2. Restore container-name endpoints:
   - `TEMPORAL_ADDRESS=temporal-ci:7233` / `temporal-smoke:7233`
   - `MINIO_ENDPOINT=minio-ci:9000` / `minio-smoke:9000`
3. Re-run workflows to verify previous behavior.

## 2026-02-12 - CI Temporal DNS/Worker Spawn Resilience

- Objective: fix CI smoke failures where worker startup reported `spawn error` and queue registration failed with temporary Temporal DNS resolution errors.
- Root cause:
  - `src/backend.worker` attempted a single Temporal connect on process start and exited immediately on transient DNS/network readiness issues.
  - `scripts/container_smoke.sh` also attempted a single Temporal client connect before poller checks.
  - Supervisor worker commands used a fixed `/usr/bin/python3` path, which is less portable across base images.
- Changes:
  - Added Temporal connect retry loop in `src/backend/worker.py` using:
    - `TEMPORAL_CONNECT_MAX_ATTEMPTS` (default `90`)
    - `TEMPORAL_CONNECT_RETRY_SECONDS` (default `2`)
  - Updated `scripts/container_smoke.sh` queue-registration step to retry Temporal connect and include `last_err` in failure output.
  - Updated worker commands in:
    - `scripts/supervisord.conf`
    - `scripts/supervisord_remote.conf`
    to use `python3 -m src.backend.worker`.

### Validation

- Re-run `CI Minimal Image Boot` workflow.
- Confirm `worker-cpu` / `worker-gpu` no longer fail immediately with `spawn error` due startup race.
- Confirm smoke step reaches `queue registration ok` without first-connect DNS failure abort.

### Rollback

1. Revert `src/backend/worker.py` Temporal retry helper and restore single connect behavior.
2. Revert retry logic in `scripts/container_smoke.sh` to previous implementation.
3. Revert worker command paths in `scripts/supervisord.conf` and `scripts/supervisord_remote.conf`.
4. Re-run CI workflow to verify baseline behavior.

## 2026-02-12 - CI Minimal Image Base Reuse Fix

- Objective: fix CI failure where app build tried to pull `cres-base-ci:<sha>` from Docker Hub instead of reusing the local base image.
- Root cause: `buildx` isolated builder could not see the image produced by the prior `load: true` step in `.github/workflows/ci-minimal-image.yml`.
- Change:
  - Updated `.github/workflows/ci-minimal-image.yml` Buildx setup to use:
    - `driver: docker`
  - This allows local image reuse in the same job for:
    - base tag: `cres-base-ci:${{ github.sha }}`
    - app build arg: `BASE_IMAGE=cres-base-ci:${{ github.sha }}`

### Validation

- Trigger `CI Minimal Image Boot` workflow.
- Confirm app image build no longer errors with:
  - `failed to resolve source metadata for docker.io/library/cres-base-ci:<sha>`
- Confirm smoke step still boots and executes:
  - `docker exec app-ci /bin/bash /workspace/scripts/container_smoke.sh`

### Rollback

1. Revert `.github/workflows/ci-minimal-image.yml` Buildx config to previous state.
2. Re-run `CI Minimal Image Boot`.
3. If needed, force base image from GHCR in app build args as an alternate path.

## 2026-02-12 - Queue Routing, Secret Hygiene, and Active-Instance Scheduling

- Objective: align runtime behavior with `cres-triage` hard constraints for queue routing, secret handling, and GPU-node resource limits.
- Changes:
  - Queue names now derive from `BASE_TASK_QUEUE` and route with suffixes:
    - CPU: `<base>@cpu`
    - GPU: `<base>@gpu`
  - Removed committed plaintext credentials from `scripts/supervisord_remote.conf` and switched to runtime environment interpolation (`%(ENV_MINIO_ACCESS_KEY)s` / `%(ENV_MINIO_SECRET_KEY)s`).
  - Aligned GPU-node runtime defaults with triage baseline:
    - llama threads `8`
    - llama offload `-ngl 999`
    - llama batch `-b 512`
    - worker `RLIMIT_AS=4GB` each
    - llama `RLIMIT_AS=3GB`
  - Updated `.env.example` from legacy Tailscale endpoints to current NAT/public defaults and added scheduler/env knobs.
  - Added active-instance scheduling guardrails in API:
    - `SCHEDULER_ACTIVE_INSTANCE=true`
    - `SCHEDULER_ACTIVE_MAX_PARALLELISM=2`
    - effective batch parallelism now capped by worker thread limits and scheduler profile.

### Validation

- Verify queue naming migration:
  - `rg "video-processing-queue|video-gpu-queue" src scripts` should return no active runtime references.
  - `scripts/container_smoke.sh` confirms pollers on `<base>@cpu` and `<base>@gpu`.
- Verify secrets no longer committed in remote supervisor config:
  - `rg "Qh@113113|AWS_SECRET_ACCESS_KEY=\\\"" scripts/supervisord_remote.conf` should not show plaintext values.
- Verify runtime limit alignment:
  - `scripts/supervisord_remote.conf`:
    - worker cpu/gpu `RLIMIT_AS=4294967296`
    - llama `LLAMA_THREADS=8,RLIMIT_AS=3221225472`
  - `start_llm.sh` and `entrypoint.sh` include `-ngl 999 --threads 8 -b 512`.
- Verify active-instance scheduler cap:
  - `src/api/main.py` computes parallelism with scheduler/thread caps and returns bounded `parallelism` in `/batch` response.

### Rollback

1. Restore previous queue constants in:
   - `src/api/main.py`
   - `src/backend/workflows.py`
   - `src/backend/worker.py`
   - `scripts/container_smoke.sh`
   - `scripts/rerun_failed_workflows.py`
2. Restore prior runtime limits and llama args in:
   - `scripts/supervisord_remote.conf`
   - `entrypoint.sh`
   - `start_llm.sh`
   - `start_remote.sh`
3. Restore previous `.env.example` values if needed for older environments.
4. Restart supervised services and run one smoke batch query.
## 2026-02-11 - Root Cleanup and Source-of-Truth Normalization

- Objective: keep a single authoritative project root at `C:\Users\rama\cres_ytdlp_norfolk`.
- Action: archived duplicate root-level project copy from `C:\Users\rama` and legacy `C:\cres_ytdlp_local`.
- Archive location: `C:\Users\rama\_archive\legacy_root_project_20260211_215608`.
- Kept launchers:
  - `C:\Users\rama\start_web_huihuang.ps1` (points to canonical `...\cres_ytdlp_norfolk\web`)
  - `C:\Users\rama\run_fastapi_norfolk.cmd` (points to canonical `...\cres_ytdlp_norfolk`)

### Validation

- `http://127.0.0.1:3000` returns `200` after restart from launcher.
- Port checks:
  - `3000` listening (web)
  - `8000` listening (FastAPI)

### Rollback

1. Stop running services on ports `3000` and `8000`.
2. Restore archived files/folders from:
   - `C:\Users\rama\_archive\legacy_root_project_20260211_215608`
3. If needed, restore legacy path:
   - `C:\cres_ytdlp_local`
4. Re-run launchers:
   - `C:\Users\rama\start_web_huihuang.ps1`
   - `C:\Users\rama\run_fastapi_norfolk.cmd`




