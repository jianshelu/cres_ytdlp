---
name: cres
description: Project brainstorm, architecture options, roadmap planning
---

# cres (Strategy / Roadmap Domain Skill)

Apply this skill for planning-domain tasks: project framing, architecture option comparison, milestone sequencing, and roadmap decisions.

Always apply `$cres-triage` first. This skill does not override topology, NAT, endpoint, queue, runtime, or security constraints defined there.

## 1) Scope

- Architecture option evaluation and phased rollout planning
- Roadmap and milestone sequencing across frontend/backend/compute workstreams
- Documentation updates in `docs/PLAN.md` and `docs/DECISIONS.md` when requested
- Task-list/schedule handoff through `$task-md` when to-do or schedule output is requested

## 2) Hard Rules

1. Keep proposals compliant with `$cres-triage` hard constraints.
2. Keep documentation diffs minimal and localized.
3. Separate facts, assumptions, and risks explicitly.
4. Every recommended action must include file, change, why, validation, and rollback.
5. Avoid speculative broad rewrites; prioritize executable next steps.
6. Never commit secrets, tokens, or private keys.

## 3) Default Workflow

1. Define objective, success criteria, and time horizon.
2. Capture current state and non-negotiable constraints from `$cres-triage`.
3. Produce 2-3 feasible options with explicit tradeoffs.
4. Recommend one path with phased milestones and dependency order.
5. Convert immediate steps into concrete file/task updates.
6. Invoke `$task-md` if the output includes to-do, schedule, or `docs/Task.md`.

## 4) Validation Baseline

- Plan is compatible with topology/NAT/FastAPI/queue constraints.
- Control-plane and compute responsibilities remain separated.
- Risks and rollback paths are explicit for each priority action.
- Each milestone has objective validation criteria.

## 5) Required Output When Invoked

1. Architecture state and governing constraints
2. Options considered and tradeoffs
3. Recommended path
4. Priority actions (top 1-3 with file/change/why/validation/rollback)
5. Required doc updates (`docs/PLAN.md`, `docs/Task.md`, `docs/DECISIONS.md`)

## 6) Definition of Done

- A constraint-compliant roadmap exists with clear milestones.
- Immediate actions are executable and assigned to concrete files/tasks.
- Validation and rollback are defined for priority actions.
- Documentation is updated consistently when requested.

## 7) Reference

Detailed option-mapping templates and review checklist:
- `./REFERENCE.md`
