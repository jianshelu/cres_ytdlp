# Compute Reference

Extended procedures for the `compute` skill. Keep `SKILL.md` as the compact rule source.

## 1) Compute File Map

- Runtime supervisor config:
  - `scripts/supervisord_remote.conf`
  - `scripts/supervisord.conf`
- llama runtime launchers:
  - `scripts/start-llama.sh`
  - `start_llm.sh`
- Worker runtime and queue attachment:
  - `src/backend/worker.py`
- Whisper and llama activity integration:
  - `src/backend/activities.py`
  - `src/backend/services/llm_llamacpp.py`
- Compute API startup and health:
  - `src/api/main.py`
- Runtime deps:
  - `requirements.instance.txt`

## 2) Fast Triage Commands (GPU Node)

Run on the GPU container/host shell:

```bash
supervisorctl -c /etc/supervisor/supervisord.conf status
```

```bash
tail -n 200 /var/log/fastapi.err
tail -n 200 /var/log/worker-gpu.err
tail -n 200 /var/log/llama.err
```

```bash
nvidia-smi
free -h
```

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8081/health
```

```bash
ls -l /workspace/src/api/main.py
ls -l /workspace/packages/models/llm
ls -l /workspace/packages/models/whisperx
```

## 3) Failure Playbook

### A) FastAPI crash loop under supervisor

1. Confirm traceback in `/var/log/fastapi.err`.
2. Verify runtime image contains app code (`/workspace/src/...`).
3. Verify startup command/module path matches repository layout.
4. Apply minimal fix in deploy target or supervisor command.
5. Restart only `fastapi` and confirm stable state.

### B) llama service fails or flaps

1. Check `llama.err` and `llama.log` for model path, wait-timeout, or binary resolution failures.
2. Confirm model sync postcondition (do not trust sync command success alone):

```bash
MODEL=/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
test -f "$MODEL" && test -r "$MODEL"
stat -c '%n %F %s' "$MODEL"
sleep 3
stat -c '%n %F %s' "$MODEL"
```

3. If symptom is "sync reports success" but file is not visible, or manual download says "File exists", treat as file-visibility anomaly and capture evidence:

```bash
ls -lah /workspace/packages/models/llm
find /workspace/packages/models/llm -maxdepth 1 -type f -name '*.gguf' -printf '%p %s\n'
df -h /workspace
mount | grep workspace || true
```

4. Correlate flap cadence with startup wait timeout before tuning:

```bash
grep -n 'LLAMA_WAIT_SECONDS' /workspace/scripts/start-llama.sh /usr/local/bin/start-llama.sh 2>/dev/null || true
```

5. Preferred order for anomaly cases: capture evidence -> controlled restart/resync -> verify stable file size -> restart `llama` only.
6. Confirm `llama-server` binary and `/app` library path are valid.
7. Use conservative tuning sequence:
   - reduce batch/parallel/context pressure first
   - adjust offload depth only after memory-pressure knobs
8. Re-check local llama health endpoint.

### C) GPU worker does not start or attach

1. Read `/var/log/worker-gpu.err` first.
2. Confirm CUDA visibility (`nvidia-smi`) and torch CUDA availability.
3. Confirm worker mode and queue suffix configuration.
4. Restart only worker process and verify poller registration.

### D) Whisper unexpectedly falls back to CPU

1. Inspect activity logs around faster-whisper model load.
2. Confirm CUDA is available when model is initialized.
3. Check model size selection and memory headroom.
4. Keep fallback behavior if GPU cannot be safely used.

## 4) Performance Tuning Order

Use the smallest-impact knob first:

1. Scheduling and concurrency:
   - worker thread counts
   - scheduler parallelism
2. Memory pressure knobs:
   - llama batch/parallel/context
   - Whisper model size
3. GPU offload depth (last)

Record every tuning change with before/after behavior and rollback value.

## 5) Validation Checklist

1. Process health:
   - supervisor status shows target services `RUNNING`
2. Endpoint health:
   - Compute API `/health` returns OK
   - llama `/health` returns OK
3. Model integrity:
   - configured model file is regular/readable and non-zero
   - file size is stable across repeated checks before `llama` launch
4. Queue behavior:
   - GPU worker identity reflects `@gpu`
   - expected GPU activities execute successfully
5. Resource sanity:
   - no sustained OOM/restart loops
   - no unintended control-plane behavior changes on GPU node

## 6) Rollback Pattern

1. Revert only files touched by the compute fix.
2. Restart only affected services (`fastapi`, `worker-gpu`, `llama`).
3. Re-run health probes and queue checks.
4. If rollback restores stability, preserve logs and document follow-up root-cause work.
