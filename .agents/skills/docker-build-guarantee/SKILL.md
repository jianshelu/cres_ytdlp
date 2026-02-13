---
name: 🐳docker-build-guarantee
description: Guarantee deterministic Docker build outcomes for this repo by enforcing preflight checks, CI buildx compatibility, llama.cpp CUDA link gates, and disk-safe dependency install policy.
---

## Objective
Stabilize image build and boot flow for this repository:
- `Dockerfile.base` build must be reproducible in CI.
- Runtime smoke checks must pass for core imports and startup scripts.
- Known failure classes must be blocked before merge.

## Use This Skill When
- User asks to fix Docker build failures in CI or GHCR publish jobs.
- `Dockerfile.base` or build workflows are changed.
- Build errors include cache backend mismatch, invalid image reference, CUDA linker errors, `apt` interactive prompts, or disk exhaustion during pip installs.

## Required Inputs
- `Dockerfile.base`
- `.github/workflows/ci-minimal-image.yml` (and related build workflows)
- `requirements.instance.txt`
- `scripts/container_smoke.sh`
- `docs/PLAN.md` (only update when architecture/ops behavior changes)

## Hard Constraints
1. No Docker-in-Docker.
2. Never commit secrets/tokens.
3. Keep minimal diffs.
4. Respect control-plane/compute split and queue routing constraints from `$cres-triage`.

## Workflow

### 1) Preflight Gates
1. Validate all `FROM` image references are syntactically valid tags.
2. If workflow uses `cache-from/cache-to type=gha`, ensure buildx driver supports it (`docker-container`), otherwise remove gha cache usage.
3. Ensure package installs are non-interactive (`DEBIAN_FRONTEND=noninteractive` + dpkg conffile options).

### 2) Dockerfile Reliability Gates
1. For llama.cpp CUDA build:
   - Ensure CUDA driver stub path is available to linker.
   - Build `llama-server` deterministically and fail with clear logs.
   - Copy artifacts via file discovery, not hardcoded unstable paths.
2. For Python dependencies:
   - Avoid downloading giant CUDA wheels when base image already includes torch.
   - Keep `pip --no-cache-dir`.
   - Remove transient caches (`/root/.cache/pip`, pycache cleanup).
3. For image size/disk pressure:
   - Remove temporary build files in same layer where possible.
   - Do not add duplicate runtime packages.

### 3) CI Workflow Gates
1. Ensure workflow explicitly sets compatible buildx driver strategy.
2. Keep smoke tests after image build:
   - import checks
   - startup checks
   - dependency endpoint/env checks (when applicable)
3. Reject workflow edits that skip dependency validation without replacement checks.

### 4) Validation Commands
Run the smallest command set that proves correctness:

```powershell
docker build -f Dockerfile.base -t cres-base-local .
docker run --rm cres-base-local python3 -c "import torch; print(torch.__version__)"
docker run --rm cres-base-local /bin/bash /workspace/scripts/container_smoke.sh
```

If local docker is unavailable, validate by CI run logs and report that local build was not executed.

## Failure Signature Mapping
- `Cache export is not supported for the docker driver`:
  buildx driver/cache backend mismatch.
- `invalid reference format` in `FROM ...:@...`:
  invalid image tag placeholder.
- `libcuda.so.1 ... undefined reference to cuMem*`:
  CUDA stub/link path issue during llama.cpp linking.
- `dpkg: ... conffile prompt ... end of file on stdin`:
  non-interactive apt/dpkg not enforced.
- `OSError: [Errno 28] No space left on device` during pip:
  oversized wheel download or layer disk pressure.
- Missing imports in smoke:
  runtime deps not present in final image.

## Output Contract
When this skill is invoked, respond with:
1. Architecture State (only relevant deltas)
2. Findings
3. Priority Actions (file, change, why, validation, rollback)
4. Patch Plan (minimal diff)
5. `docs/PLAN.md` update suggestion when ops behavior changes

## Rollback Policy
1. Revert only touched build/workflow lines.
2. Restore last known green base image tag/workflow settings.
3. Re-run smoke checks to confirm rollback safety.
