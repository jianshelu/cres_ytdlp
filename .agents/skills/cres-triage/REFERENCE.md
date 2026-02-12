# cres-triage Reference Manual

This file carries detailed operational context that supports `SKILL.md`.
If there is a conflict, `SKILL.md` remains authoritative.

## Architecture Details

### Network flow

`Norfolk (LAN) -> SSH -> huihuang (Control Plane) -> NAT (64.229.113.233) -> Vast.ai floating GPU`

### Host responsibilities

| Host | Responsibilities |
|---|---|
| Norfolk | Development client only |
| huihuang | Temporal, MinIO, web UI, Control API |
| GPU node | GPU worker, optional CPU worker, llama.cpp, Whisper, Compute API |

## Worker Design

### Queue naming and routing

- CPU queue: `<base_task>@cpu`
- GPU queue: `<base_task>@gpu`
- Example: `metadata@cpu`, `transcribe@gpu`

### Startup checks for `@gpu`

1. `nvidia-smi` succeeds.
2. GPU memory is available.
3. Model paths exist or missing-model fallback is applied.

If checks fail, do not start `@gpu` worker.

## Runtime Constraints (Detailed)

### Memory budget

- Background RAM limit: `7 GB` total.
- Suggested split: `3 GB` llama.cpp + `4 GB` workers.
- Under pressure: reduce worker concurrency first.

### llama.cpp settings

- Offload: `-ngl 999`
- Batch: `-b 512`
- Threads: `--threads 8`

Tune order for OOM risk:
1. Lower `-b`.
2. Lower `-ngl` only if necessary.

### Model paths

- LLM: `/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`
- Whisper: `/workspace/packages/models/whisperx`

Fallback behavior:
- Missing LLM file: skip llama start.
- Missing Whisper directory: disable Whisper features.
- Missing models must not crash whole service.

## Validation Checklist

### On GPU node

- `nvidia-smi`
- Confirm `@gpu` worker is registered in Temporal.
- `nc -zv 64.229.113.233 7233`
- `curl http://64.229.113.233:9000`
- `curl http://localhost:8000`

### On Norfolk

- `curl http://192.168.2.130:3000`

## Troubleshooting Patterns

| Symptom | Likely cause | Action |
|---|---|---|
| GPU tasks run on CPU worker | Queue suffix/routing mismatch | Enforce `@gpu` suffix on GPU-bound tasks |
| GPU worker not visible in Temporal | Connectivity or startup-check failure | Validate public Temporal endpoint and startup checks |
| VRAM/OOM instability | Batch/offload too aggressive for runtime state | Reduce `-b`; reduce `-ngl` only if needed |
| Web cannot be reached remotely | Expected behavior | Web is LAN-only by design |

## Extended DoD Notes

A change is stable when:
- VRAM usage is predictable.
- RAM stays under the background budget.
- No OOM kills or restart loops occur.
- llama server stays responsive.
- Worker connection to Temporal remains healthy.
