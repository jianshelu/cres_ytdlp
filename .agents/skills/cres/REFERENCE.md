# cres Reference

Use this reference only when deeper planning detail is needed.

## Option Comparison Template

- Option name
- What changes (files/services)
- Benefits
- Risks
- Validation checks
- Rollback approach

## Milestone Template

- Milestone objective
- Entry criteria
- Exit criteria (measurable)
- Owner domain (frontend/backend/compute)
- Dependencies

## Risk Review Checklist

- Violates `$cres-triage` constraints? (must be no)
- Changes endpoint exposure? (must be explicit)
- Affects queue suffix routing (`@cpu`/`@gpu`)? (must stay compliant)
- Requires `docs/PLAN.md` update?
- Requires `docs/Task.md` update via `$task-md`?
- Requires `docs/DECISIONS.md` tradeoff record?
