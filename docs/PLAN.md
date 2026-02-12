# PLAN

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

