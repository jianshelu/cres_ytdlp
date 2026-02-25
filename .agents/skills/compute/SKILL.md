---
name: compute
description: GPU runtime, llama.cpp, Whisper, performance/resource constraints
---

# compute (GPU Runtime Domain Skill)

Apply this skill for compute-domain tasks on the GPU side: runtime boot issues, llama.cpp and Whisper behavior, worker GPU execution, and performance/resource tuning.

Always apply `$triage` first. This skill does not override topology, endpoint, queue, or hard runtime constraints defined there.

## 1) Scope

- GPU runtime process management (`supervisord`, service logs, startup order)
- llama.cpp runtime behavior and serving health
- Whisper runtime behavior (GPU/CPU fallback, model loading)
- Model sync integrity checks for LLM/Whisper paths before service start
- GPU worker startup and queue polling behavior
- Compute API startup/health verification

## 2) Hard Rules

1. Keep diffs minimal and localized.
2. Prefer runtime config and env fixes before code rewrites.
3. Keep control-plane responsibilities out of compute-side fixes.
4. Preserve queue suffix routing semantics (`@cpu` / `@gpu`) when touching worker flow.
5. Never commit secrets, tokens, or private keys.
6. Use log evidence first, then patch.
7. Never treat model sync as successful without post-sync file checks (regular file, readable, non-zero stable size).
8. Keep instance image bundle focused on GPU runtime required services; do not expand by default with non-GPU/control-plane modules.

## 3) Default Workflow

1. Classify the issue:
   - startup crash
   - degraded throughput/latency
   - memory pressure/OOM
   - incorrect GPU/CPU fallback behavior
   - model sync or file-visibility anomaly
2. Collect evidence from supervisor status, service logs, health probes, and model-path file checks.
3. Patch the smallest root-cause file first (runtime config/scripts before deep code changes).
4. Tune in safe order:
   - reduce memory pressure knobs with lowest behavior risk first
   - preserve model/service availability
   - only then change deeper runtime offload settings
5. Re-validate end-to-end (service health plus queue worker registration).

## 4) Validation Baseline

- Verify `fastapi`, `llama`, and required worker processes are stable.
- Verify Compute API health and dependency checks.
- Verify configured model paths are valid regular files/directories and file size is stable before launching compute services.
- If `llama` flaps roughly every 30 minutes, correlate with model wait timeout before changing performance knobs.
- Verify GPU worker polls expected queue suffix and can execute activities.
- Verify no control-plane or exposure-rule drift was introduced.
- Verify image/runtime bundle contains required GPU files (`src/backend`, `src/shared`, `src/api/compute`, runtime configs/scripts).

## 5) Required Output When Invoked

1. Architecture state (compute-side only)
2. Findings with concrete log/file evidence
3. Priority actions (file, change, why, validation, rollback)
4. Patch plan (minimal diff)
5. Whether `docs/PLAN.md` requires update

## 6) Definition of Done

- Compute services start cleanly and remain stable.
- llama.cpp and Whisper behavior match requested runtime mode.
- GPU worker is healthy and correctly routed.
- Performance/resource tuning resolves the issue without architectural rule violations.

## 7) Reference

Detailed command playbook and troubleshooting matrix:
- `./REFERENCE.md`
