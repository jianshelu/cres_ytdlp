---
name: backend
description: APIs, Temporal workflows, queue routing, and control-plane backend services
---

# backend (Control-Plane / Workflow Domain Skill)

Apply this skill for backend-domain tasks: Control API behavior, workflow orchestration, queue routing logic, and control-plane service operations.

Always apply `$cres-triage` first. This skill does not override topology, NAT, endpoint, queue, or runtime constraints defined there.

## 1) Scope

- Control API code under `src/api/**`
- Workflow/activity orchestration under `src/backend/**`
- Queue routing and dispatch semantics (`@cpu` / `@gpu`)
- Control-plane backend startup scripts/config (`scripts/start_control_plane_boot.ps1`, `scripts/supervisord*.conf`)
- Backend-related deploy/runtime guards in `.github/workflows/**` when requested

## 2) Hard Rules

1. Keep diffs minimal and localized.
2. Preserve dual FastAPI separation (control API on huihuang; compute API on GPU node).
3. Preserve queue suffix routing semantics (`<base>@cpu`, `<base>@gpu`) end-to-end.
4. Never route GPU-required activities to `@cpu`.
5. Do not introduce endpoint exposure beyond triage NAT/public rules.
6. Prefer evidence-first diagnosis (logs/health/queue state) before patching.
7. Redact secrets/tokens from logs before sharing excerpts.
8. Never commit secrets, tokens, or private keys.

## 3) Default Workflow

1. Classify the backend issue:
   - API contract/validation
   - workflow start/dispatch
   - activity execution routing
   - worker poller registration
   - startup/deploy runtime mismatch
2. Collect concrete evidence:
   - failing route/workflow IDs
   - queue names and suffixes
   - control API health and dependency checks
   - relevant supervisor/service logs
3. Patch the smallest root-cause surface first (config/routing before broad refactor).
4. Validate in this order:
   - API health
   - queue routing correctness
   - single workflow smoke path
5. Update `docs/PLAN.md` only when architecture/ops behavior changes.

## 4) Validation Baseline

- Control API health endpoint returns expected status.
- Queue naming remains suffix-safe (`@cpu`, `@gpu`) in API/workflow/worker paths.
- Worker registration/polling aligns with requested mode and queue ownership.
- No control-plane drift into compute-only responsibilities.

## 5) Required Output When Invoked

1. Architecture state (backend/control-plane relevant)
2. Findings with concrete log/file evidence
3. Priority actions (file, change, why, validation, rollback)
4. Patch plan (minimal diff)
5. Whether `docs/PLAN.md` must be updated

## 6) Definition of Done

- Control API contract and health are correct.
- Workflow dispatch and queue routing are correct and suffix-safe.
- Backend changes respect triage architecture and endpoint constraints.
- Validation checks pass with no new security/exposure drift.

## 7) Reference

Detailed diagnostics, validation commands, and rollback playbook:
- `./REFERENCE.md`
