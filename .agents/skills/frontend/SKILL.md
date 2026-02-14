---
name: 🌐🎨 Frontend
description: UI and web integration for the Next.js frontend in this repo.
---

# frontend (UI/Web Domain Skill)

Apply this skill for frontend tasks: routes, pages, components, styles, and frontend API integration.

Always apply `$triage` first. This skill does not override topology, routing, or runtime constraints from triage.

## 1) Scope

- Next.js app-router pages under `web/src/app/**`
- Shared components and client logic under `web/src/app/components/**`
- Global and route-level styling under `web/src/app/globals.css` and related CSS modules
- Frontend API proxy routes under `web/src/app/api/**`

## 2) Hard Constraints

1. Use minimal diffs; avoid broad rewrites.
2. Preserve existing route behavior unless the task explicitly changes it.
3. Keep backend contracts stable unless API changes are explicitly requested.
4. Reuse existing design tokens and UI patterns before introducing new ones.
5. Handle missing media/data gracefully in UI (fallback text/links/states).
6. Never commit secrets/tokens in frontend code, env files, or docs.
7. Do not introduce deployment/network exposure changes from frontend-only work.

## 3) Default Workflow

1. Map the request to exact files/routes/components first.
2. Implement server/client split intentionally:
   - Server components for data loading and request-derived context.
   - Client components for interactivity, local state, and media controls.
3. Keep URL/media normalization consistent with existing app helpers.
4. Add only the CSS needed for the target UI surface.
5. Validate with frontend build and route smoke checks.

## 4) Validation Baseline

- `cd web && npm run build`
- Manual route checks for changed pages (desktop and mobile width)
- Confirm new UI does not break existing `/`, `/video/[id]`, `/transcriptions`, `/sentence` flows

## 5) Required Output When Invoked

1. Files changed
2. Validation steps and results
3. Rollback steps
4. Whether `docs/PLAN.md` update is needed (only if architecture/ops behavior changes)

## 6) Definition of Done

- Frontend build passes.
- New/updated route renders and behaves as requested.
- Existing routes remain functional.
- No architecture or security rule violations.

## 7) Reference

Detailed implementation playbook and troubleshooting:
- `./REFERENCE.md`
