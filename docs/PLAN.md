# PLAN
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



