# backend REFERENCE

Extended backend diagnostics and validation playbook for this repo.

Use with `SKILL.md`. Do not override `$triage`.

## 1) Responsibility Map

- `src/api/main.py`: control API health, scheduling, workflow trigger paths
- `src/api/routers/**`: request contract and API surface
- `src/backend/workflows.py`: workflow-level orchestration and queue handoff
- `src/backend/activities.py`: activity implementations and side effects
- `src/backend/worker.py`: worker mode, queue polling, and worker identity
- `scripts/start_control_plane_boot.ps1`: control-plane boot orchestration on huihuang
- `scripts/supervisord*.conf`: runtime process wiring and queue/env configuration

## 2) Fast Checks (Static)

```powershell
rg --line-number "BASE_TASK_QUEUE|CPU_TASK_QUEUE|GPU_TASK_QUEUE|@cpu|@gpu" src/api src/backend scripts
```

```powershell
rg --line-number "TEMPORAL_ADDRESS|MINIO_ENDPOINT|LLAMA_HEALTH_URL|SCHEDULER_ACTIVE" src/api scripts
```

```powershell
rg --line-number "src.api.main:app|WORKER_MODE|video-processing" scripts src
```

## 3) Fast Checks (Runtime)

- Control API health:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

- If running on Linux host/container:

```bash
supervisorctl status
tail -n 200 /var/log/fastapi.err
tail -n 200 /var/log/fastapi.log
```

- Validate app import path in runtime context:

```bash
python3 -c "import importlib; importlib.import_module('src.api.main'); print('ok')"
```

## 4) Recurring Failure Patterns

1. FastAPI crash loop with supervisor `exit status 1`:
   - Check `/var/log/fastapi.err` first.
   - Verify runtime has the app source path (`src/api/main.py`) and correct launch target (`src.api.main:app`).
2. Queue routing regressions:
   - Ensure all routing uses `<base>@cpu` and `<base>@gpu` consistently.
   - Reject unsuffixed queue names for backend workflow/worker routing.
3. Endpoint drift:
   - Keep endpoint usage aligned with triage NAT/public constraints.
   - Avoid accidental LAN-only endpoint usage in GPU-side runtime configuration.

## 5) Validation Sequence

1. Run static queue and endpoint scans.
2. Verify control API health endpoint response.
3. Verify worker process mode and queue polling state.
4. Execute one targeted workflow smoke path before broader reruns.

## 6) Log Hygiene

- Never commit logs containing credentials, tokens, or keys.
- Before sharing log excerpts, redact secrets and access tokens.

## 7) Rollback Template

1. Revert only touched backend files.
2. Restart impacted backend services/workers.
3. Re-run the same smoke checks used for validation.
4. Confirm queue/endpoint behavior has returned to baseline.

## 8) PLAN Update Rule

Update `docs/PLAN.md` only when architecture or ops behavior changes
(endpoint exposure, routing policy, process ownership, or deployment path).
