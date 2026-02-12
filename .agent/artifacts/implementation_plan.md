# Implementation Plan - cres_ytdlp Project

Time Zone Standard: `America/Toronto` (EST/EDT).

| Date | Models/Systems | Threads | Status | Completion Time (America/Toronto) |
| :--- | :--- | :--- | :--- | :--- |
| 2026-02-08 | Temporal + FastAPI + Next.js + llama.cpp | Combined Keywords Feature Compliance | `[DONE]` | 10:54:14 |
| 2026-02-08 | Artifact System | OBLONG Consolidation | `[DONE]` | 11:19:16 |
| 2026-02-09 | Temporal Orchestrator + Frontend + Batch Test Harness | Unified Orchestration and UX Stabilization | `[DONE]` | 00:41:30 |
| 2026-02-09 | Workflow Runtime + Combined Sentence/Video + Cache/UX | Platform Baseline Lock (Do-Not-Rollback) | `[DONE]` | 02:30:00 |
| 2026-02-09 | Control Plane Migration + LAN Web Hosting + Runtime Recovery | Hybrid Topology Cutover | `[DONE]` | 23:40:00 |
| 2026-02-10 | Local Control Plane + Remote GPU Worker + Service Recovery | Hybrid Runtime Stabilization | `[DONE]` | 02:33:01 |

---

## Date: 2026-02-08 // Combined Keywords Feature Compliance

* Plan 1: Verify feature implementation against [Combined Keywords Feature.md](../../Combined Keywords Feature.md)
  * Context: Need requirement-by-requirement validation across backend + frontend.
  * Outcome: Clear compliance matrix and identified gaps.
  * Strategy: Inspect API router, keyword/sentence services, frontend pages/components, CSS layout behavior.
  * Scope: `src/api/routers/transcriptions.py`, `src/backend/services/keyword_service.py`, `src/backend/services/llm_llamacpp.py`, `src/backend/services/sentence_service.py`, `web/src/app/page.tsx`, `web/src/app/transcriptions/page.tsx`, `web/src/app/transcriptions/TranscriptionsClient.tsx`, `web/src/app/globals.css`.

* Plan 2: Confirm runtime/deployment constraints for Vast.ai flow
  * Context: Production deployment and remote debugging must align with existing Vast.ai practices.
  * Outcome: Keep implementation compatible with GHCR image deployment + tunnel/Temporal workflow.
  * Strategy: Follow [.agent/rules/workwithvastai.md](../rules/workwithvastai.md) conventions for infra and naming.
  * Scope: GHCR deployment path, SSH tunnel workflow, Temporal workflow naming and suffix policy.

## Date: 2026-02-08 // OBLONG State Consolidation

* Plan 3: Consolidate state across artifacts
  * Context: User issued `[ OBLONG ]` command requiring cross-artifact synchronization.
  * Outcome: ToC synced, ledger advanced, walkthrough anchored, knowledge distilled.
  * Strategy: Append-only updates to [implementation_plan.md](implementation_plan.md), [task_list.md](task_list.md), [walkthrough.md](walkthrough.md), [knowledge_base.md](knowledge_base.md).
  * Scope: `.agent/artifacts/*.md`.

## Date: 2026-02-09 // Unified Orchestration and UX Stabilization

* Plan 4: Move batch execution into single long-running orchestrator workflow with rollback mode
  * Context: User requested test-stage operation under one workflow process instead of dispatcher spawning child batch workflows.
  * Outcome: `/batch` requests are queued and executed inline in one orchestrator workflow; rollback path remains available.
  * Strategy: Add `QueryOrchestratorWorkflow` for inline pipeline execution, keep `QueryDispatcherWorkflow + BatchProcessingWorkflow` as legacy mode, route by env switch in API.
  * Scope: `src/backend/workflows.py`, `src/backend/worker.py`, `src/api/main.py`.

* Plan 5: Build reproducible Google-to-YouTube test harness for Chinese AI queries
  * Context: Need a standalone script to fetch current Google news signals, derive keywords, and trigger bounded YouTube pipeline jobs.
  * Outcome: Repeatable smoke/regression test path with JSON reports and explicit runtime parameters.
  * Strategy: Implement script that fetches Google RSS, extracts up to 10 keywords, dispatches `/batch` with `max_duration_minutes<=10`, and writes run report artifacts.
  * Scope: `scripts/google_ai_pipeline_test.py`, `.agent/artifacts/google_ai_pipeline_report*.json`.

* Plan 6: Stabilize transcriptions UX and combined sentence source coverage
  * Context: User reported combined key sentences biased to first video and combined video playback progress reset on scroll.
  * Outcome: Key sentences cover multiple transcripts; combined video playback time remains stable while page scrolls.
  * Strategy: Switch sentence extraction from concatenated-text-first-match to transcript-coverage-first extraction; guard player reload effect with stable refs and idempotent clip key checks.
  * Scope: `src/backend/services/sentence_service.py`, `src/backend/activities.py`, `src/api/routers/transcriptions.py`, `web/src/app/transcriptions/TranscriptionsClient.tsx`.

* Plan 7: Rework home page into vertical waterfall marquee grouped by query
  * Context: User requested non-playing carousel-style marquee rows per search query.
  * Outcome: Home page shows query-grouped marquee rows from top to bottom; each row loops that query's results.
  * Strategy: Replace grid/sidebar composition with grouped rows and CSS marquee animations, preserving query navigation links.
  * Scope: `web/src/app/page.tsx`, `web/src/app/globals.css`.

## Date: 2026-02-09 // Artifact Detail Expansion (Doc-Aligned)

* Plan 8: Align artifacts with `docs/Implementation Plan.md` structure depth
  * Context: Current artifacts are accurate but less detailed than the project reference docs.
  * Outcome: Detailed, strategy-first records with clear thread granularity and stable temporal continuity.
  * Strategy: Expand each artifact with explicit objective, dependencies, execution logic, and verification evidence.
  * Scope: `.agent/artifacts/implementation_plan.md`, `.agent/artifacts/task_list.md`, `.agent/artifacts/walkthrough.md`, `.agent/artifacts/knowledge_base.md`.

* Plan 9: Expand Perimeter detail using `docs/Perimeter.md` sections
  * Context: Perimeter should serve as technical source-of-truth for infra/runtime decisions and incident handling.
  * Outcome: Richer tables for Env Specs, Infra Ledger, Magazine, Bug Log, and Optimization.
  * Strategy: Add service dependency topology, runtime mode switches, script interfaces, and troubleshooting patterns from recent operations.
  * Scope: `.agent/artifacts/knowledge_base.md`.

* Plan 10: Expand operational history fidelity from `docs/Walkthrough.md`
  * Context: Need clearer chain from problem signal to root cause to production verification.
  * Outcome: Walkthrough entries become actionable postmortems usable for rollback/on-call handoff.
  * Strategy: Record execution phases by symptom category (workflow, cache, frontend deploy, playback, sentence extraction) with validation points.
  * Scope: `.agent/artifacts/walkthrough.md`.

* Plan 11: Increase ledger precision with sequential continuity from `docs/Task.md`
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

* Plan 12: Lock workflow dispatch model to per-query batch workflow
  * Context: User validated this model as expected production/test behavior.
  * Outcome: One keyword query starts one `BatchProcessingWorkflow`; five keywords create five independent workflows.
  * Strategy: `/batch` directly starts `BatchProcessingWorkflow.run`; no shared dispatcher/orchestrator queue in active path.
  * Scope: `src/api/main.py`, Temporal runtime verification.
  * Guardrail: Do not reintroduce global queue orchestrator as default path without explicit user approval.

* Plan 13: Persist combined video as backend artifact (not frontend-only dynamic stitching)
  * Context: Dynamic clip stitching in frontend produced unstable short combined playback and made historical data hard to refresh.
  * Outcome: Combined video is generated server-side from key-sentence segments and stored in MinIO as canonical artifact.
  * Strategy: Rebuild script generates `queries/<slug>/combined/combined-video.mp4` with ffmpeg and updates combined metadata.
  * Scope: `scripts/rebuild_combined_output.py`, `src/api/routers/transcriptions.py`, MinIO combined object contract.
  * Guardrail: Keep `combined_video_url` as preferred playback source when available.

* Plan 14: Make cache forward-compatible with new combined schema
  * Context: Old cache entries lacked `key_sentences` and `combined_video_url`, masking new behavior.
  * Outcome: API detects incomplete cache payload and recomputes response to refresh cache.
  * Strategy: Cache-read compatibility checks before return; fallback to recompute when required fields are missing.
  * Scope: `src/api/routers/transcriptions.py`.
  * Guardrail: New combined fields (`key_sentences`, `combined_video_url`, `recombined_sentence`, `sentence_version`) are required for cache hits.

* Plan 15: Mark rebuilt combined sentence/video explicitly for auditability
  * Context: Need visible evidence that historical results were rebuilt by new logic.
  * Outcome: Rebuilt outputs carry explicit version/flag metadata.
  * Strategy: Store and expose:
    * `recombined_sentence: true`
    * `combined_sentence_version: "recombined-v2"`
    * `combined_rebuilt_at_utc`
  * Scope: MinIO combined output + API response + frontend badge.
  * Guardrail: Any future rebuild strategy must bump `combined_sentence_version`.

## Date: 2026-02-09 // Remote Runtime Freeze + Incremental Artifact Closeout

* Plan 16: Lock deployment behavior to remote instance build/restart only
  * Context: Local build verification did not reflect user-visible runtime state.
  * Outcome: Frontend/backend changes are validated only after remote sync and remote service restart.
  * Strategy: Use instance-side source sync, remote `next build`, and targeted restart of affected services.
  * Scope: `web` runtime release flow, operational scripts and runbook conventions.
  * Guardrail: Avoid local-only build conclusions for UI behavior acceptance.

* Plan 17: Finalize marquee interaction policy for readability
  * Context: Continuous fast motion across all rows caused visual noise and poor scanability.
  * Outcome: Non-hover rows run slower; hovered row runs faster with explicit fixed duration policy.
  * Strategy: Separate animation timing for idle vs hover states and deploy/tune on instance.
  * Scope: `web/src/app/globals.css`, `web/src/app/page.tsx`.
  * Guardrail: Keep default speed proportional to item count readability, not raw animation loop speed.

* Plan 18: Close this cycle with commit baseline and manual instance shutdown handoff
  * Context: User manually shut down remote instance after runtime validation.
  * Outcome: Repository state and artifact documents record the tested baseline and shutdown status.
  * Strategy: Persist final operational facts (commit, push, shutdown owner, pending resume checks) into artifacts.
  * Scope: `.agent/artifacts/*.md`, git baseline tracking.
  * Guardrail: Do not reopen architecture decisions implicitly in later sessions without explicit request.

## Date: 2026-02-09 // Hybrid Topology Cutover (Afternoon/Evening Backfill)

* Plan 23: Transition from in-instance full stack to LAN-hosted control plane/web
  * Context: User moved Temporal/MinIO/web responsibilities to LAN server and kept instance primarily for GPU workloads.
  * Outcome: Service ownership boundaries were redefined across hosts.
  * Strategy: Shift runtime endpoints and startup scripts from single-host defaults to cross-host addresses.
  * Scope: deployment/run scripts, env variables, host runbooks.

* Plan 24: Validate and repair access paths after tunnel/proxy churn
  * Context: Connect scripts, reverse tunnel assumptions, and host reboot caused intermittent service inaccessibility.
  * Outcome: Direct LAN access to web was restored and conflicting forwarding assumptions were reduced.
  * Strategy: re-test each service path independently (web, API, Temporal UI, MinIO UI) and remove stale proxy dependencies.
  * Scope: operational connection scripts, endpoint checks, startup sequence.

* Plan 25: Align index update flow with new web host authority
  * Context: Workflows and MinIO objects completed successfully but homepage did not reflect new results.
  * Outcome: Reindex ownership and callback path became explicit under LAN web host model.
  * Strategy: keep API-side reindex endpoint reachable from worker host and ensure generated index lands on production web host.
  * Scope: `refresh_index` activity behavior, API admin endpoint, web data source placement.

* Plan 26: Restore stable worker runtime after host role split
  * Context: During migration, worker placement briefly diverged and dependency/runtime mismatches appeared.
  * Outcome: Final rule set clarified: workers execute on instance, control plane/web on LAN host.
  * Strategy: normalize worker startup to instance and keep dependency set complete there.
  * Scope: worker runtime env, startup commands, dependency packaging.

## Date: 2026-02-10 // Hybrid Runtime Stabilization

* Plan 19: Migrate web and API serving baseline to `huihuang` LAN server, keep GPU-heavy execution on Vast instance
  * Context: User moved Web/FastAPI/Temporal/MinIO control functions to LAN host and kept Whisper/LLM-heavy workload on instance.
  * Outcome: Control plane and user-facing web stabilized on LAN host; worker execution path clarified.
  * Strategy: Align env and startup scripts with LAN control plane endpoints; avoid stale local machine paths.
  * Scope: deployment scripts, runtime env, startup/runbook procedures.

* Plan 20: Harden cross-host index refresh and object visibility after workflow completion
  * Context: Workflows completed and objects appeared in MinIO, but homepage did not show new query results.
  * Outcome: Reindex callback path verified and refresh flow made explicit between instance worker and LAN API/web host.
  * Strategy: Keep `REINDEX_URL` callback reachable from instance, add fallback local index generation behavior, and verify `data.json` source-of-truth host.
  * Scope: `src/backend/activities.py`, runtime env config, operational checks.

* Plan 21: Recover worker activity execution by correcting runtime dependencies on instance
  * Context: Temporal showed no running activities and failure `No module named 'faster_whisper'`.
  * Outcome: Worker runtime dependency expectations documented and aligned with "all workers on instance" final decision.
  * Strategy: Keep Whisper dependency resolved in instance runtime where GPU execution happens; avoid drift between hosts.
  * Scope: worker runtime image/env and startup sequence.

* Plan 22: Performance evaluation pass for multi-video keyword workflows
  * Context: User requested comparison between `阿里千问` and `开源模型` workflow runs and optimization space.
  * Outcome: Download/transcribe/summarize critical path and latency contributors identified; optimization backlog updated.
  * Strategy: Compare completed run durations and activity timeline shape, then prioritize queue/concurrency and network-path tuning.
  * Scope: Temporal workflow timelines, `download_video` / `transcribe_video` / `summarize_content` activities, network path to external control plane.

* Plan 27: Perform full artifact reconciliation and generate explicit missing-item backfill list
  * Context: Long session compaction raised risk of partial history gaps and visible text corruption in artifacts.
  * Outcome: Chronological ordering corrected, visible garble fixed, and a recorded/missing checklist produced.
  * Strategy: Audit artifacts against logs and pipeline report outputs, then store results in a dedicated reconciliation document.
  * Scope: `.agent/artifacts/*.md`, `logs/instance.log`, `.agent/artifacts/google_ai_pipeline_report*.json`.



