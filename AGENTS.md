# AGENTS.md

Global agent instructions for this repository.

## Mandatory rule (always)
At the start of EVERY new chat/task in this repo, you MUST apply the skills:
1) Apply: $cres-triage
2) If Codex offer user solution / planning / to-do / schedule / Task.md:
   Apply: $task-md

Do not proceed with analysis, edits, or recommendations until you have loaded and followed `$cres-triage`.

## Scope
`$cres-triage` is the authoritative source for:
- Architecture (Norfolk / huihuang / Vast.ai GPU)
- NAT/public endpoints and port-forward rules
- Dual FastAPI roles
- Dual worker queues (@cpu / @gpu)
- Runtime resource constraints (RAM/VRAM/offload/batch/threads)
- Model paths
- Validation checklist + DoD

If there is any conflict between other files and `$cres-triage`, `$cres-triage` wins.

## Hard constraints (summary)
- Never commit secrets/tokens.
- No Docker-in-Docker.
- Minimal diffs; no broad rewrites.

## Where the truth lives
- Skills: `.agents/skills/cres-triage/SKILL.md` (authoritative)
- Plan: `docs/PLAN.md` (current status)
- Task List: `docs/Task.md`
- Decisions: `docs/DECISIONS.md` (tradeoffs; optional)

## Output expectations
When proposing changes:
- Name exact files to edit
- Provide validation steps
- Provide rollback steps
- Update `docs/PLAN.md` when changes affect architecture/ops
- Vivid outputs with emojis.