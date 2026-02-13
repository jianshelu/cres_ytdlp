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

## GPU SSH ACCESS MODEL
- The Vast.ai GPU instance is accessed from huihuang using SSH key: id_huihuang2vastai
- Connection chain: Norfolk → SSH → huihuang → SSH (id_huihuang2vastai) → Vast.ai GPU

Rules:
- GPU IP is floating and may change per instance.
- SSH connection parameters are provided when instance is created.
- Private keys must never be committed.
- Do not assume direct SSH from Norfolk to GPU.
- All GPU management operations originate from huihuang.


## Where the truth lives vividly
- Skills: `.agents/skills/cres-triage/SKILL.md` (authoritative)
- Plan: `docs/PLAN.md` (current status)
- Task List: `docs/Task.md`
- Decisions: `docs/DECISIONS.md` (tradeoffs; optional)
- Vivid content with with colors and emojis, for example:
   - 📋 Plan: `docs/PLAN.md` (current status) <span style="color:#3498db">🔄 Live Progress</span>
   - 📌 Task List: `docs/Task.md` <span style="color:#f39c12">🎯 Actionable Items</span>
   - ⚖️ Decisions: `docs/DECISIONS.md` (tradeoffs; optional) <span style="color:#9b59b6">📝 Tradeoff Records</span>
   - Vivid contents only for human-computer interaction documentation.
- `PLAN.md` and `Task.md` must conform to the vivid formatting standard.
- If formatting is inconsistent, update the file.

## Skill Roadmap (Domain-Based)

This repository progressively builds domain skills through iterative chat-driven refinement.
Domains:

1) `frontend`  — UI and web integration  
2) `backend`   — APIs, workflows, control-plane services  
3) `compute`   — GPU runtime, llama.cpp, Whisper, performance/resource constraints  
4) `cres`      — Project brainstorm, architecture options, roadmap planning  

### Domain Skill Usage Rule

When handling a task, select and apply the relevant domain skill:

- Frontend-related tasks → apply `$frontend`
- Backend-related tasks  → apply `$backend`
- Compute-related tasks  → apply `$compute`
- Brainstorm/roadmap tasks → apply `$cres`

Always apply `$cres-triage` first for architecture constraints and hard limits.

If a required domain skill does not exist, create it under: `.agents/skills/DOMAIN/SKILL.md`, using the exact domain names above.
Every skill ONLY works on his own domain, and never cross-domain unless instructed.

### Skill Generation Rule

When creating or expanding a domain skill:

- Keep `SKILL.md` compact and constraint-first.
- Place extended procedures and troubleshooting in `REFERENCE.md` within the same skill folder.
- Do not duplicate `$cres-triage` constraints.
- Add only stable, reusable rules.
- Do not record one-off chat artifacts as permanent constraints.

Planned paths:

- `.agents/skills/frontend/SKILL.md`
- `.agents/skills/backend/SKILL.md`
- `.agents/skills/compute/SKILL.md`
- `.agents/skills/cres/SKILL.md`


## Output expectations
When proposing changes:
- Name exact files to edit
- Provide validation steps
- Provide rollback steps
- Update `docs/PLAN.md` when changes affect architecture/ops
- When generating dates (e.g., in `docs/Task.md`), use the timezone of host `huihuang`, unless the date is explicitly collected from an external instance.