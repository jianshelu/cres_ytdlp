---
name: task-md
description: Generate or update docs/Task.md as a daily task list (day -> work category -> tasks).
---

## Objective
Maintain a single source-of-truth task file at: `docs/Task.md`.

## Task.md Structure (Mandatory)
- Group by **day** (YYYY-MM-DD, Montreal time).
- Under each day, group by **work category** (small category).
- Under each category, list **atomic tasks** (checkbox items).
- Each task should be actionable, testable, and small.

### Template
# Tasks

## YYYY-MM-DD (DayName)
### <Work Category A>
- [ ] <Task 1> (owner: <optional>, link: <optional>, notes: <optional>)
- [ ] <Task 2>

### <Work Category B>
- [ ] <Task 1>

## YYYY-MM-DD
...

## Inputs (Always read first)
- `docs/PLAN.md` (current focus)
- `docs/DECISIONS.md` (if exists)
- Recent user instructions in chat

## Rules
1) If `docs/Task.md` does NOT exist:
   → Create it using the template.

2) If it exists:
   → Update today's section if present.
   → Otherwise prepend a new day section at the top.

3) Do NOT delete historical days unless explicitly instructed.

4) Each work category should contain ≤ 7 active tasks.
   If overflow occurs:
   → Move extras under a subsection: "Upcoming".

5) Tasks must start with verbs:
   Fix / Implement / Verify / Refactor / Document / Test / Configure / Deploy.

6) Unfinished tasks may be UPDATED when:
   - User instructions change
   - Project plan (docs/PLAN.md) changes
   - Architecture constraints change
   - Priority changes

   Updating means:
   - Edit wording
   - Change category
   - Split into smaller tasks
   - Merge redundant tasks
   - Re-prioritize within the same day

   Do NOT blindly append duplicates.
   Maintain clarity and avoid task drift.

7) If a task is completed:
   - Mark as [x]
   - Do not remove it (unless user explicitly requests cleanup)

------------------------------------------------------------
Recommended Work Categories (for this repo)
------------------------------------------------------------

- Temporal
- MinIO
- Web
- Control API
- llama
- Whisper
- Compute API
- Workers & Queues (@cpu / @gpu)
- Networking & NAT (64.229.113.233 / Port Forwarding)
- Resource & Performance (RAM / VRAM / Batch / Threads)
- Docs & Ops (Runbook / Validation / Architecture)

------------------------------------------------------------
Output Requirements (in chat)
------------------------------------------------------------

After updating file, report:

- File modified: docs/Task.md
- Day updated: YYYY-MM-DD
- Categories affected
- Whether tasks were added, modified, split, or reprioritized