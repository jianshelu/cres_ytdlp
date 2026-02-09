# Walkthrough - cres_ytdlp Project History

Time Zone Standard: `America/Toronto` (EST/EDT).

## Date: 2026-02-08 // OBLONG State Consolidation

* **Plan Statement:** Consolidate current project state into persistent artifacts and align with global architectural tracking protocol.
* **Root Cause/Findings:** Only one artifact file existed ([.agent/artifacts/task_list.md](task_list.md)), so required artifact set was incomplete for protocol-level continuity.
* **Final Solution:** Created [.agent/artifacts/implementation_plan.md](implementation_plan.md), [.agent/artifacts/walkthrough.md](walkthrough.md), and [.agent/artifacts/knowledge_base.md](knowledge_base.md); appended task ledger with sequential items and updated timestamps.
* **Verification:** Confirmed artifact files present and updated under `.agent/artifacts/`.

## Date: 2026-02-08 // Foundation for Next Phase

* **Next Execution Anchor:** Continue with requirement-by-requirement compliance for [Combined Keywords Feature.md](../../Combined Keywords Feature.md), with pass/fail list and remediation points.

## Date: 2026-02-09 // Unified Orchestration and UX Stabilization

* **Plan Statement:** Collapse query processing into a single long-running orchestrator workflow for test mode, preserve rollback path, and fix UX regressions in transcriptions and homepage rendering.
* **Root Cause/Findings:**
  * Batch architecture complexity was high for test-phase operations; user requested one workflow process model.
  * Combined key sentence generation was biased to first transcript because extraction scanned one merged text block and returned first matches.
  * Combined video progress reset on scroll due to replay/seek effects re-firing on render churn.
  * Home page waterfall marquee changes were not visible on instance until remote build + restart.
* **Final Solution:**
  * Added inline execution flow in orchestrator mode and runtime mode switch (`inline`/`legacy`) for rollback compatibility.
  * Introduced `scripts/google_ai_pipeline_test.py` to fetch Google signals, derive keywords, dispatch bounded `/batch` runs, and emit report JSON.
  * Reworked sentence extraction to transcript-coverage-first strategy and updated both batch artifact generation and API fallback path.
  * Hardened transcriptions player clip loading with stable memoized data and idempotent clip key checks to preserve playback position during page scroll.
  * Replaced homepage grid/sidebar with query-grouped vertical marquee rows and deployed to vast.ai instance.
* **Verification:**
  * `/batch` responses report orchestrator mode as `inline` with accepted request IDs.
  * Worker logs confirm `QueryOrchestratorWorkflow` inline activity chain execution.
  * Anti-gravity query now yields multi-source key sentences instead of first-video-only output.
  * Frontend build succeeded (
ext build`) and instance restart returned `3000:200` and `8000:200` after targeted service restarts.

## Date: 2026-02-09 // Artifact Detail Expansion (Doc-Referenced)

* **Plan Statement:** Increase artifact depth and operational readability by aligning records with the richer templates in `docs/Implementation Plan.md`, `docs/Perimeter.md`, `docs/Task.md`, and `docs/Walkthrough.md`.
* **Root Cause/Findings:**
  * Existing artifact set was structurally correct but lighter than reference documents in terms of dependency mapping and incident chronology.
  * Some high-value operational details (service dependency chain, mode switch rationale, rollout/restart behavior, cache alias issues) were present in chat history but not fully consolidated.
  * Ledger continuity required explicit numbering for major post-OBLONG changes (workflow architecture switch, pipeline harness, sentence extraction fixes, homepage deployment).
* **Final Solution:**
  * Expanded Implementation Plan with a new doc-aligned detail expansion phase and explicit reference mapping table.
  * Extended Task List with sequential tasks `25-40`, marking completed orchestration/deployment/UX fixes and defining concrete pending follow-ups.
  * Added detailed walkthrough entry with problem-class segmentation and production verification anchors.
  * Enriched Perimeter with deeper infra/runtime tables: mode switches, service topology, troubleshooting, and optimization patterns.
* **Verification:**
  * Artifact files updated and readable with preserved continuity:
    * `.agent/artifacts/implementation_plan.md`
    * `.agent/artifacts/task_list.md`
    * `.agent/artifacts/walkthrough.md`
    * `.agent/artifacts/knowledge_base.md`
  * Format consistency validated manually against doc references (plan fields, ledger sequencing, walkthrough narrative shape, perimeter section set).

## Date: 2026-02-09 // Baseline Lock: Workflow + Recombined Sentence Video

* **Plan Statement:** Freeze validated runtime baseline and write explicit anti-rollback constraints into project artifacts.
* **Root Cause/Findings:**
  * Team iterations introduced multiple runtime modes (dispatcher/orchestrator/inline), increasing risk of accidental rollback to undesired behavior.
  * Frontend dynamic combined video stitching caused short/unstable playback and inconsistent historical query experience.
  * Old cache payloads hid new combined sentence/video fields, making rebuilt behavior appear absent.
* **Final Solution:**
  * Locked `/batch` active path to direct per-query `BatchProcessingWorkflow` start:
    * one query => one workflow
    * five queries => five workflows
    * per-query video activities remain inside that query's workflow.
  * Implemented historical rebuild pipeline via `scripts/rebuild_combined_output.py`:
    * recompute combined sentence/key sentences
    * generate server-side combined video (`ffmpeg`)
    * write MinIO artifact `queries/<slug>/combined/combined-video.mp4`
    * persist version flags (ecombined_sentence`, `combined_sentence_version`, `combined_rebuilt_at_utc`).
  * Updated transcriptions API/frontend contract:
    * API returns `combined_video_url`, ecombined_sentence`, `sentence_version`
    * frontend prefers prebuilt combined video when present
    * cache compatibility guard forces recompute if required new fields are missing.
* **Verification:**
  * Temporal checks showed `workflow_type=BatchProcessingWorkflow` for independent keyword runs.
  * Bulk historical rebuild completed with zero failures (`--all --refresh-index`).
  * Query checks (e.g., `科技之光`, `记忆系统`, `Oracle`) returned:
    * `combined_video_url` present
    * ecombined_sentence=true`
    * `sentence_version=recombined-v2`.

## Date: 2026-02-09 // Remote Deployment Policy + Instance Shutdown Closeout

* **Plan Statement:** Close the iteration with remote-first deployment rules, final marquee readability tuning, and explicit shutdown handoff status.
* **Root Cause/Findings:**
  * Local build outputs were not reliable indicators of the live vast.ai behavior.
  * Homepage marquee perceived speed remained too high until runtime tuning was applied and revalidated on instance.
  * User manually terminated instance after stabilization and requested incremental artifact consolidation.
* **Final Solution:**
  * Locked operational rule to remote sync/build/restart for acceptance checks.
  * Tuned marquee behavior so non-hover rows are slower and hovered row uses fixed faster duration target.
  * Preserved tested code baseline in git and documented closure state for next startup session.
* **Verification:**
  * Baseline commit recorded on `main`: `9ed118b`.
  * Working tree confirmed clean at artifact closeout time.
  * Instance shutdown ownership recorded as manual user action (post-validation).



