# Implementation Plan - cres_ytdlp Project

| Date 📅 | Models/Systems ⚙️ | Threads 🧵 | Status 🚦 | Completion Time ⏱️ |
| :--- | :--- | :--- | :--- | :--- |
| 2026-02-08 | Temporal + FastAPI + Next.js + llama.cpp | Combined Keywords Feature Compliance | `[DONE]` | 10:54:14 |
| 2026-02-08 | Artifact System | OBLONG Consolidation | `[DONE]` | 11:19:16 |
| 2026-02-09 | Temporal Orchestrator + Frontend + Batch Test Harness | Unified Orchestration and UX Stabilization | `[DONE]` | 00:41:30 |
| 2026-02-09 | Workflow Runtime + Combined Sentence/Video + Cache/UX | Platform Baseline Lock (Do-Not-Rollback) | `[DONE]` | 02:30:00 |

---

## Date: 2026-02-08 // Combined Keywords Feature Compliance

* 🧵 Plan 1: Verify feature implementation against [Combined Keywords Feature.md](../../Combined Keywords Feature.md)
  * Context: Need requirement-by-requirement validation across backend + frontend.
  * Outcome: Clear compliance matrix and identified gaps.
  * Strategy: Inspect API router, keyword/sentence services, frontend pages/components, CSS layout behavior.
  * Scope: `src/api/routers/transcriptions.py`, `src/backend/services/keyword_service.py`, `src/backend/services/llm_llamacpp.py`, `src/backend/services/sentence_service.py`, `web/src/app/page.tsx`, `web/src/app/transcriptions/page.tsx`, `web/src/app/transcriptions/TranscriptionsClient.tsx`, `web/src/app/globals.css`.

* 🧵 Plan 2: Confirm runtime/deployment constraints for Vast.ai flow
  * Context: Production deployment and remote debugging must align with existing Vast.ai practices.
  * Outcome: Keep implementation compatible with GHCR image deployment + tunnel/Temporal workflow.
  * Strategy: Follow [.agent/rules/workwithvastai.md](../rules/workwithvastai.md) conventions for infra and naming.
  * Scope: GHCR deployment path, SSH tunnel workflow, Temporal workflow naming and suffix policy.

## Date: 2026-02-08 // OBLONG State Consolidation

* 🧵 Plan 3: Consolidate state across artifacts
  * Context: User issued `[ OBLONG ]` command requiring cross-artifact synchronization.
  * Outcome: ToC synced, ledger advanced, walkthrough anchored, knowledge distilled.
  * Strategy: Append-only updates to [implementation_plan.md](implementation_plan.md), [task_list.md](task_list.md), [walkthrough.md](walkthrough.md), [knowledge_base.md](knowledge_base.md).
  * Scope: `.agent/artifacts/*.md`.

## Date: 2026-02-09 // Unified Orchestration and UX Stabilization

* 🧵 Plan 4: Move batch execution into single long-running orchestrator workflow with rollback mode
  * Context: User requested test-stage operation under one workflow process instead of dispatcher spawning child batch workflows.
  * Outcome: `/batch` requests are queued and executed inline in one orchestrator workflow; rollback path remains available.
  * Strategy: Add `QueryOrchestratorWorkflow` for inline pipeline execution, keep `QueryDispatcherWorkflow + BatchProcessingWorkflow` as legacy mode, route by env switch in API.
  * Scope: `src/backend/workflows.py`, `src/backend/worker.py`, `src/api/main.py`.

* 🧵 Plan 5: Build reproducible Google-to-YouTube test harness for Chinese AI queries
  * Context: Need a standalone script to fetch current Google news signals, derive keywords, and trigger bounded YouTube pipeline jobs.
  * Outcome: Repeatable smoke/regression test path with JSON reports and explicit runtime parameters.
  * Strategy: Implement script that fetches Google RSS, extracts up to 10 keywords, dispatches `/batch` with `max_duration_minutes<=10`, and writes run report artifacts.
  * Scope: `scripts/google_ai_pipeline_test.py`, `.agent/artifacts/google_ai_pipeline_report*.json`.

* 🧵 Plan 6: Stabilize transcriptions UX and combined sentence source coverage
  * Context: User reported combined key sentences biased to first video and combined video playback progress reset on scroll.
  * Outcome: Key sentences cover multiple transcripts; combined video playback time remains stable while page scrolls.
  * Strategy: Switch sentence extraction from concatenated-text-first-match to transcript-coverage-first extraction; guard player reload effect with stable refs and idempotent clip key checks.
  * Scope: `src/backend/services/sentence_service.py`, `src/backend/activities.py`, `src/api/routers/transcriptions.py`, `web/src/app/transcriptions/TranscriptionsClient.tsx`.

* 🧵 Plan 7: Rework home page into vertical waterfall marquee grouped by query
  * Context: User requested non-playing carousel-style marquee rows per search query.
  * Outcome: Home page shows query-grouped marquee rows from top to bottom; each row loops that query's results.
  * Strategy: Replace grid/sidebar composition with grouped rows and CSS marquee animations, preserving query navigation links.
  * Scope: `web/src/app/page.tsx`, `web/src/app/globals.css`.

## Date: 2026-02-09 // Artifact Detail Expansion (Doc-Aligned)

* 🧵 Plan 8: Align artifacts with `docs/Implementation Plan.md` structure depth
  * Context: Current artifacts are accurate but less detailed than the project reference docs.
  * Outcome: Detailed, strategy-first records with clear thread granularity and stable temporal continuity.
  * Strategy: Expand each artifact with explicit objective, dependencies, execution logic, and verification evidence.
  * Scope: `.agent/artifacts/implementation_plan.md`, `.agent/artifacts/task_list.md`, `.agent/artifacts/walkthrough.md`, `.agent/artifacts/knowledge_base.md`.

* 🧵 Plan 9: Expand Perimeter detail using `docs/Perimeter.md` sections
  * Context: Perimeter should serve as technical source-of-truth for infra/runtime decisions and incident handling.
  * Outcome: Richer tables for Env Specs, Infra Ledger, Magazine, Bug Log, and Optimization.
  * Strategy: Add service dependency topology, runtime mode switches, script interfaces, and troubleshooting patterns from recent operations.
  * Scope: `.agent/artifacts/knowledge_base.md`.

* 🧵 Plan 10: Expand operational history fidelity from `docs/Walkthrough.md`
  * Context: Need clearer chain from problem signal to root cause to production verification.
  * Outcome: Walkthrough entries become actionable postmortems usable for rollback/on-call handoff.
  * Strategy: Record execution phases by symptom category (workflow, cache, frontend deploy, playback, sentence extraction) with validation points.
  * Scope: `.agent/artifacts/walkthrough.md`.

* 🧵 Plan 11: Increase ledger precision with sequential continuity from `docs/Task.md`
  * Context: Task ledger should remain continuous across sessions while preserving done/pending visibility.
  * Outcome: New entries appended with strict sequential numbering and completion timestamps.
  * Strategy: Add detailed completion entries for orchestrator migration, pipeline harness, UX fixes, and artifact expansion.
  * Scope: `.agent/artifacts/task_list.md`.

### Reference Mapping (Docs -> Artifacts)

| Reference Doc | Reused Pattern | Applied File |
| :--- | :--- | :--- |
| `docs/Implementation Plan.md` | Context/Outcome/Strategy/Scope per plan thread | `.agent/artifacts/implementation_plan.md` |
| `docs/Perimeter.md` | Env/Infra/Magazine/Bug/Optimization depth | `.agent/artifacts/knowledge_base.md` |
| `docs/Task.md` | Continuous sequential ledger with done markers | `.agent/artifacts/task_list.md` |
| `docs/Walkthrough.md` | Plan -> Findings -> Solution -> Verification narrative | `.agent/artifacts/walkthrough.md` |

## Date: 2026-02-09 // Platform Baseline Lock (Do-Not-Rollback)

* 🧵 Plan 12: Lock workflow dispatch model to per-query batch workflow
  * Context: User validated this model as expected production/test behavior.
  * Outcome: One keyword query starts one `BatchProcessingWorkflow`; five keywords create five independent workflows.
  * Strategy: `/batch` directly starts `BatchProcessingWorkflow.run`; no shared dispatcher/orchestrator queue in active path.
  * Scope: `src/api/main.py`, Temporal runtime verification.
  * Guardrail: Do not reintroduce global queue orchestrator as default path without explicit user approval.

* 🧵 Plan 13: Persist combined video as backend artifact (not frontend-only dynamic stitching)
  * Context: Dynamic clip stitching in frontend produced unstable short combined playback and made historical data hard to refresh.
  * Outcome: Combined video is generated server-side from key-sentence segments and stored in MinIO as canonical artifact.
  * Strategy: Rebuild script generates `queries/<slug>/combined/combined-video.mp4` with ffmpeg and updates combined metadata.
  * Scope: `scripts/rebuild_combined_output.py`, `src/api/routers/transcriptions.py`, MinIO combined object contract.
  * Guardrail: Keep `combined_video_url` as preferred playback source when available.

* 🧵 Plan 14: Make cache forward-compatible with new combined schema
  * Context: Old cache entries lacked `key_sentences` and `combined_video_url`, masking new behavior.
  * Outcome: API detects incomplete cache payload and recomputes response to refresh cache.
  * Strategy: Cache-read compatibility checks before return; fallback to recompute when required fields are missing.
  * Scope: `src/api/routers/transcriptions.py`.
  * Guardrail: New combined fields (`key_sentences`, `combined_video_url`, `recombined_sentence`, `sentence_version`) are required for cache hits.

* 🧵 Plan 15: Mark rebuilt combined sentence/video explicitly for auditability
  * Context: Need visible evidence that historical results were rebuilt by new logic.
  * Outcome: Rebuilt outputs carry explicit version/flag metadata.
  * Strategy: Store and expose:
    * `recombined_sentence: true`
    * `combined_sentence_version: "recombined-v2"`
    * `combined_rebuilt_at_utc`
  * Scope: MinIO combined output + API response + frontend badge.
  * Guardrail: Any future rebuild strategy must bump `combined_sentence_version`.
