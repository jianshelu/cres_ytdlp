# Knowledge Base (Perimeter) - cres_ytdlp

Time Zone Standard: `America/Toronto` (EST/EDT).

## Date: 2026-02-08 // OBLONG Consolidation

### Env Specs

| Area | Dev (Local) | Deployment (Vast.ai) |
| :--- | :--- | :--- |
| OS/Host | Windows 11 + local editor | Vast.ai GPU instance |
| Runtime Delivery | Local source edits | Docker/runtime services |
| LLM Serving | Local/remote `llama.cpp` endpoint | `llama-server` on instance |

### Infra Ledger

| Topic | Current Rule/Fact | Notes |
| :--- | :--- | :--- |
| Connectivity | SSH tunnel based workflow | Required for local web/API access |
| Workflow Engine | Temporal task queue orchestration | Keep workflow IDs deterministic |
| Object Storage | MinIO bucket `cres` | Query-scoped paths under `queries/<slug>/...` |

### Magazine

| Subject | Source of Truth | Practical Guidance |
| :--- | :--- | :--- |
| Deployment build strategy | `.agent/rules/workwithvastai.md` | Incremental image/build and safe restarts |
| Artifact governance | `.agent/artifacts/GEMINI.md` | Additive persistence and date-anchored sessions |
| Naming policy | backend slug functions | Keep consistent query slug naming |

### Bug Log

| Date | Issue | Resolution |
| :--- | :--- | :--- |
| 2026-02-08 | Artifact set incomplete | Added required artifact files |

### ? Optimization

| Area | Guidance | Rationale |
| :--- | :--- | :--- |
| GPU balance | Keep transcription + LLM concurrency controlled | Prevent service stalls |
| Model/data sync | Keep `/workspace/packages/models` stable | Reduce cold start failures |

## Date: 2026-02-09 // Orchestrator, Test Harness, and UX Stabilization

### Env Specs

| Area | Dev (Local) | Deployment (Vast.ai) |
| :--- | :--- | :--- |
| Batch mode switch | Env var `BATCH_ORCHESTRATOR_MODE` | `inline` default, `legacy` rollback |
| Frontend release mode | Local 
ext build` validation | Must run build on instance before 
ext start` |
| Script execution | Standalone script invocation | `google_ai_pipeline_test.py` no bootstrap coupling |

### Infra Ledger

| Topic | Investigation | Resolution |
| :--- | :--- | :--- |
| API down after orchestration change | Import mismatch between deployed files | Re-sync `main.py/workflows.py/worker.py`, restart api+worker |
| Home page UI not updated | Source synced but stale production build | Build on instance + restart Next only |
| Query path mismatch | `Antigravity` vs `Anti gravity` slugs diverged | Recompute sentence artifacts for both slugs and clear cache |

### Magazine

| Subject | What Was Added | Why It Matters |
| :--- | :--- | :--- |
| Unified workflow model | `QueryOrchestratorWorkflow` inline execution | Easier temporal traceability in test phase |
| Rollback compatibility | `legacy` mode retains dispatcher+batch path | Fast fallback without code revert |
| Batch test harness | `scripts/google_ai_pipeline_test.py` | Reproducible Google?keyword?YouTube pipeline tests |
| Sentence extraction model | Transcript-coverage-first evidence selection | Prevents first-video sentence bias |
| Home content rendering | Query-grouped waterfall marquee rows | Better browsing density without autoplay |

### Bug Log

| Date | Issue | Root Cause | Resolution |
| :--- | :--- | :--- | :--- |
| 2026-02-09 | Key sentences only from first video | Single merged-text first-match extraction | Added transcript-coverage-first extraction path |
| 2026-02-09 | Combined video progress reset on scroll | Clip load effect re-triggered on render churn | Added memoized source list + clip-key guard |
| 2026-02-09 | Home marquee not visible on instance | No remote rebuild after source sync | Build + targeted Next restart |

### ? Optimization

| Area | Pattern | Effect |
| :--- | :--- | :--- |
| Orchestrator history control | Continue-as-new threshold for long-running queue | Keeps workflow history bounded |
| Activity stability | Inline pipeline with bounded parallelism per request | Predictable GPU/CPU pressure |
| Frontend behavior | Idempotent clip loading and reduced unnecessary seeks | Smooth playback continuity while scrolling |

## Date: 2026-02-09 // Perimeter Deepening (Reference-Driven)

### Env Specs

| Domain | Local Dev Runtime | Vast.ai Runtime | Operational Note |
| :--- | :--- | :--- | :--- |
| API orchestration mode | `BATCH_ORCHESTRATOR_MODE` optional in local env | Default `inline` unless explicitly set to `legacy` | Enables zero-code rollback behavior |
| Frontend release cycle | Local 
pm run build` used for compile checks | Must run remote 
pm run build` before 
ext start` | Source sync alone does not update live pages |
| Temporal client usage | Local tooling may lack `temporalio` package | Worker/API always run inside instance python env | Query verification should run in-instance |
| Data index source | `web/src/data.json` can be local stale snapshot | `/workspace/web/src/data.json` is live source-of-truth | Always regenerate index on instance after storage changes |

### Infra Ledger

| Layer | Endpoint/Port | Dependency | Failure Signature | Resolution Pattern |
| :--- | :--- | :--- | :--- | :--- |
| Next.js UI | `:3000` | Reads `web/src/data.json`, calls `/api/*` | Old UI despite source changes | Remote build + restart Next only |
| FastAPI | `:8000` | Temporal client + MinIO + llama | `500` or health `code=000` | Resync API/workflow files and restart api+worker |
| Temporal Worker | task queue `video-processing-queue` | Activities + models + MinIO | Workflow accepted but no progression | Inspect `/var/log/worker.log`, verify worker PID |
| llama.cpp | `:8081` | Summarize/keyword extraction | Fallback keyword mode triggered repeatedly | Keep fallback paths, monitor model health |
| MinIO | `:9000` (`cres` bucket) | videos/transcripts/combined/cache | stale cache or alias divergence | delete scoped cache keys + regenerate artifacts |

### Magazine

| Subject | Key Components | Command / Interface | Notes |
| :--- | :--- | :--- | :--- |
| Unified orchestration | `QueryOrchestratorWorkflow` + inline pipeline helper | `POST /batch` | Queue signal + inline activity chain in single workflow run |
| Rollback architecture | `QueryDispatcherWorkflow` + `BatchProcessingWorkflow` | `BATCH_ORCHESTRATOR_MODE=legacy` | Legacy child-workflow mode retained for rollback |
| Pipeline harness | `scripts/google_ai_pipeline_test.py` | `python scripts/google_ai_pipeline_test.py ...` | Fetches Google RSS -> extracts keywords -> dispatches bounded batches |
| Combined output builder | `build_batch_combined_output` | activity in worker | Writes `queries/<slug>/combined/combined-output.json` |
| Sentence extraction model | `SentenceService.extract_combined_sentence_from_transcripts` | backend service call | Coverage-first extraction across transcripts, then keyword backfill |

### Bug Log

| Date | Bug | Trigger | Impact | Fix |
| :--- | :--- | :--- | :--- | :--- |
| 2026-02-09 | Combined key sentence from first video only | Sentence extraction on merged blob with first-match behavior | Poor cross-video representation in Key Sentences/Combined Video | Coverage-first transcript extraction + artifact recompute |
| 2026-02-09 | Scroll caused combined video progress reset | Clip load effect re-fired after render churn / sticky state transitions | Playback jumped back to clip start (key sentence point) | Added memoized video list and clip-key idempotent guard |
| 2026-02-09 | Homepage marquee not visible after code change | Remote runtime still serving previous build | User saw old grid layout | Deploy source + run remote build + restart Next |
| 2026-02-09 | Query alias split (`Antigravity` vs `Anti gravity`) | Different slug normalization paths over time | Separate combined outputs/caches created | Recompute both slugs + clear cache branch |

### ? Optimization

| Area | Tactic | Operational Benefit |
| :--- | :--- | :--- |
| Task throughput | Per-request bounded parallelism (`1..4`) | Prevents worker saturation on small RAM instances |
| Temporal traceability | Single orchestrator timeline in test phase | Easier debugging of activity ordering and latency |
| Cache control | Targeted key deletion instead of full bucket purge | Faster reset cycles with lower collateral impact |
| Frontend stability | Avoid unnecessary media source/seek resets | Maintains uninterrupted playback during UI state changes |
| Deployment safety | Restart only affected services (`api+worker` or 
ext`) | Minimizes disruption to Temporal/MinIO/llama services |

## Date: 2026-02-09 // Incremental Closeout (Manual Instance Shutdown)

### Env Specs

| Area | Rule | Note |
| :--- | :--- | :--- |
| Runtime validation | Remote instance is source of truth | Local build is non-authoritative for final UX acceptance |
| Release baseline | Git commit `9ed118b` on `main` | Stabilized workflow + combined rebuild + marquee controls |
| Instance state | Manually shut down by user | Next session must include cold-start health check |

### Infra Ledger

| Topic | Final State | Next Session Requirement |
| :--- | :--- | :--- |
| Frontend marquee tuning | Applied and pushed | Verify timing perception after reboot with real query rows |
| Workflow baseline | Per-query `BatchProcessingWorkflow` preserved | Confirm no accidental fallback to dispatcher/orchestrator mode |
| Artifact continuity | Incremental append model retained | Continue sequential updates only; no rewrite of historical sections |

### Bug Log

| Date | Issue | Current Status |
| :--- | :--- | :--- |
| 2026-02-09 | Marquee perceived as too fast on instance | Tuned and redeployed; pending reboot-time reconfirmation |
| 2026-02-09 | Confusion about latest query freshness on homepage | Not yet addressed; add explicit latest-query marker next |

### Optimization

| Area | Guidance | Rationale |
| :--- | :--- | :--- |
| Cold-start recovery | Run service health + one smoke query before heavy tests | Avoid false negatives after instance reboot |
| UX readability | Prefer stable idle motion and explicit hover acceleration | Reduces motion fatigue on dense query rows |



