# PLAN

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

