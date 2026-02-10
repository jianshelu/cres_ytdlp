# Task List - cres_ytdlp Project

Time Zone Standard: `America/Toronto` (EST/EDT).

**Maintained by:** Antigravity  
**Project:** YouTube Video Processing & Transcription with LLM Analysis  
**Sequential Task Numbering:** Continuous across all sessions

---

## Date: 2026-02-08

### Completed Tasks

- [x] **1.** Fix Temporal workflow argument passing mechanism (tuple parameter standardization) `[DONE 10:31:21]`
- [x] **2.** Deploy workflow fixes to Vast.ai instance and verify execution `[DONE 10:31:21]`
- [x] **3.** Successfully test Oracle batch workflow with single video processing `[DONE 10:38:36]`
- [x] **4.** Implement keyword highlighting in Key Sentences section `[DONE 10:41:42]`
- [x] **5.** Convert transcription display to horizontal slide frame layout `[DONE 10:41:42]`
- [x] **6.** Verify feature compliance against [Combined Keywords Feature.md](../../Combined Keywords Feature.md) spec `[DONE 10:49:55]`
- [x] **7.** Refactor frontend to use FastAPI backend /api/transcriptions endpoint `[DONE 10:54:14]`
- [x] **8.** Enforce 5-video limit per specification requirement `[DONE 10:54:14]`
- [x] **9.** Implement collapsible combined sentence with click-to-expand UI `[DONE 10:54:14]`
- [x] **10.** Add individual transcript download buttons (per video column) `[DONE 10:54:14]`
- [x] **11.** Add "Download All Transcripts" batch functionality `[DONE 10:54:14]`
- [x] **12.** Fix video filtering logic in backend API (search_query field) `[DONE 10:54:14]`
- [x] **13.** Create environment configuration for frontend API URL `[DONE 10:54:14]`
- [x] **14.** Deploy specification-compliant implementation to instance `[DONE 10:54:14]`

### Pending/In-Progress Tasks

- [ ] **15.** Test end-to-end workflow: Search -> LLM Keyword Extraction -> UI Display
- [ ] **16.** Verify LLM server (llama.cpp) is responding correctly to keyword extraction requests
- [ ] **17.** Monitor coverage compensation algorithm performance with real data
- [ ] **18.** Test download functionality in browser environment
- [ ] **19.** Validate combined sentence quality and keyword highlighting accuracy
- [ ] **20.** Performance testing: API response time with 5 concurrent videos
- [ ] **21.** Error handling verification: Test API fallback when LLM is unavailable

---

## Notes

### Today's Focus Areas
- **Temporal Workflow Stability:** Fixed critical argument passing bug affecting batch processing
- **Specification Compliance:** Full implementation of [Combined Keywords Feature.md](../../Combined Keywords Feature.md) requirements
- **Backend-Frontend Integration:** Connected Next.js to FastAPI for LLM-powered keyword extraction
- **UI/UX Features:** Collapsible sections, download buttons, horizontal slider navigation

### Known Issues
- LLM server health check needs verification (not tested in current session)
- Coverage compensation algorithm untested with real multi-video scenarios
- Frontend may need CORS configuration if API and Next.js are on different origins

### Next Session Priorities
1. End-to-end testing with real search queries
2. LLM integration verification
3. Performance benchmarking
4. User acceptance testing

---

**Last Updated:** 2026-02-08 10:57:11 (America/Toronto)

---

## Date: 2026-02-08 // OBLONG State Consolidation

### Completed Tasks

- [x] **22.** Ingest and apply project rules from [.agent/rules/workwithvastai.md](../rules/workwithvastai.md) and [GEMINI.md](C:/Users/ruipe/.gemini/GEMINI.md) `[DONE 11:19:16]`
- [x] **23.** Execute OBLONG deep state consolidation across artifact set `[DONE 11:19:16]`

### Pending/In-Progress Tasks

- [ ] **24.** Resume and finalize requirement-by-requirement verification report for [Combined Keywords Feature.md](../../Combined Keywords Feature.md)

---

**Last Updated:** 2026-02-08 11:19:16 (America/Toronto)

---

## Date: 2026-02-09

### Completed Tasks

- [x] **25.** Implement single-workflow inline orchestration mode (`QueryOrchestratorWorkflow`) with queue signal processing `[DONE 00:12:10]`
- [x] **26.** Preserve rollback compatibility via legacy dispatcher/batch mode switch in API (`BATCH_ORCHESTRATOR_MODE`) `[DONE 00:12:10]`
- [x] **27.** Register new orchestrator workflow in worker and deploy api/worker to instance `[DONE 00:13:40]`
- [x] **28.** Verify `/batch` accepted responses and inline orchestrator execution in Temporal worker logs `[DONE 00:15:00]`
- [x] **29.** Create standalone Google-to-YouTube pipeline test harness (`scripts/google_ai_pipeline_test.py`) `[DONE 00:18:50]`
- [x] **30.** Add dry-run/report outputs and bounded query dispatch (`max_duration_minutes<=10`) `[DONE 00:20:05]`
- [x] **31.** Run smoke/latest pipeline checks and confirm 10 accepted dispatches `[DONE 00:21:30]`
- [x] **32.** Redesign homepage into query-grouped vertical waterfall marquee (non-autoplay cards) `[DONE 00:24:10]`
- [x] **33.** Deploy homepage marquee updates to Vast.ai and rebuild Next.js runtime `[DONE 00:25:50]`
- [x] **34.** Fix combined sentence bias (first-video dominance) by transcript-coverage-first extraction `[DONE 00:34:20]`
- [x] **35.** Recompute `antigravity/anti-gravity` combined sentence artifacts and clear stale transcription cache `[DONE 00:40:15]`
- [x] **36.** Fix transcriptions combined-video progress reset during scroll (clip load idempotency guard) `[DONE 00:41:30]`
- [x] **37.** Expand artifacts detail level using `docs/Implementation Plan.md`, `docs/Perimeter.md`, `docs/Task.md`, `docs/Walkthrough.md` as reference `[DONE 00:58:40]`

### Pending/In-Progress Tasks

- [ ] **38.** Add automated artifact lint/check script (section presence + sequential task numbering validation)
- [ ] **39.** Add dashboard summary script for query-by-query output completeness (`combined-output.json`, sentence, keywords, manifest)
- [ ] **40.** Add periodic cache invalidation strategy for query aliases (`antigravity` vs `anti-gravity`) to avoid divergence

---

**Last Updated:** 2026-02-09 00:58:40 (America/Toronto)

---

## Date: 2026-02-09 // Incremental Closeout

### Completed Tasks

- [x] **41.** Enforce remote-first validation rule: deploy/build/restart on vast.ai instance for UI acceptance `[DONE 22:47:00]`
- [x] **42.** Tune homepage marquee readability policy (idle slower, hover faster fixed target) and redeploy `[DONE 22:50:00]`
- [x] **43.** Monitor multi-workflow running status and continue stable per-query workflow baseline verification `[DONE 22:53:00]`
- [x] **44.** Commit and push stabilized baseline to `origin/main` (`9ed118b`) `[DONE 22:56:00]`
- [x] **45.** Record manual remote instance shutdown and perform artifact incremental consolidation `[DONE 23:01:00]`

### Pending/In-Progress Tasks

- [ ] **46.** On next instance boot, run post-start verification checklist (`3000/8000` health, one query smoke, sentence page render)
- [ ] **47.** Add small UI marker on homepage indicating latest query batch timestamp for easier freshness judgment

---

**Last Updated:** 2026-02-09 23:01:00 (America/Toronto)

---

## Date: 2026-02-09 // Afternoon-Evening Backfill

### Completed Tasks

- [x] **63.** Complete topology decision to host web/control-plane services on `huihuang` and keep GPU execution on instance `[DONE 16:40:00]`
- [x] **64.** Resolve LAN web accessibility regression by removing conflicting proxy/tunnel assumptions `[DONE 17:05:00]`
- [x] **65.** Re-check API batch submit path after endpoint migration and normalize request target format `[DONE 17:30:00]`
- [x] **66.** Sync runtime configuration after instance endpoint changes and SSH access updates `[DONE 18:10:00]`
- [x] **67.** Validate Temporal completion + MinIO object generation for Oracle query under new topology `[DONE 18:45:00]`
- [x] **68.** Diagnose homepage no-result state as index authority/reindex-path mismatch across hosts `[DONE 19:20:00]`
- [x] **69.** Migrate/re-align FastAPI hosting to `huihuang` service model and re-verify health `[DONE 20:05:00]`
- [x] **70.** Restore worker placement policy to instance-only execution after temporary split experiments `[DONE 20:50:00]`

### Pending/In-Progress Tasks

- [ ] **71.** Add explicit runbook section for cross-host ownership (web/api/index/worker) to avoid future endpoint ambiguity
- [ ] **72.** Add automated post-cutover validation script (web/API/Temporal/MinIO plus one smoke batch)

---

**Last Updated:** 2026-02-10 02:45:00 (America/Toronto)

---

## Date: 2026-02-10 // Reconciliation Pass

### Completed Tasks

- [x] **73.** Execute full artifact reconciliation (time-order scan + text-quality scan + evidence cross-check) `[DONE 02:51:47]`
- [x] **74.** Generate explicit recorded/missing checklist from logs and pipeline reports (`reconciliation_checklist_2026-02-10.md`) `[DONE 02:51:47]`

### Pending/In-Progress Tasks

- [ ] **75.** Add SSL probe protocol-mismatch issue (`HTTP_REQUEST` on TLS endpoint) into Knowledge Base bug ledger with mitigation
- [ ] **76.** Add RSS feed text-encoding normalization and keyword quality guardrails into pipeline backlog
- [ ] **77.** Add low-priority SSH auth-noise hardening checklist for instance connection scripts

---

**Last Updated:** 2026-02-10 02:51:47 (America/Toronto)

---

## Date: 2026-02-10

### Completed Tasks

- [x] **48.** Re-validate post-reboot service accessibility and recover LAN-hosted web/API reachability on `huihuang` `[DONE 00:32:00]`
- [x] **49.** Correct broken batch submit URL pathing causing `API 502` (`Failed to parse URL` / `fetch failed`) `[DONE 00:45:00]`
- [x] **50.** Verify instance-to-control-plane connectivity model after tailscale removal and public port-forward migration `[DONE 00:58:00]`
- [x] **51.** Establish stable division: control plane/web on LAN host, GPU worker runtime on instance `[DONE 01:10:00]`
- [x] **52.** Diagnose `No worker running` by tracing Temporal failure payloads and worker runtime state `[DONE 01:18:00]`
- [x] **53.** Resolve activity blocker `ModuleNotFoundError: faster_whisper` in instance execution path `[DONE 01:25:00]`
- [x] **54.** Re-run English-news Google->YouTube bounded pipeline (<=3 keywords, <=3 videos/keyword) after worker recovery `[DONE 01:40:00]`
- [x] **55.** Monitor `阿里千问` workflow run with 8 target videos and confirm end-to-end completion `[DONE 01:58:00]`
- [x] **56.** Validate `build_batch_combined_output` for `阿里千问` with non-empty combined output metrics `[DONE 02:03:00]`
- [x] **57.** Compare optimized runtime behavior between `阿里千问` and `开源模型` workflow executions `[DONE 02:18:00]`
- [x] **58.** Add 2026-02-10 incremental updates to artifacts (plan/walkthrough/task/perimeter) `[DONE 02:33:01]`

### Pending/In-Progress Tasks

- [ ] **59.** Implement activity queue split (`download` vs `transcribe/summarize`) with explicit concurrency caps
- [ ] **60.** Add workflow-level performance report export (per-activity latency and critical path summary)
- [ ] **61.** Add startup self-check script to verify worker dependency set before registering Temporal worker
- [ ] **62.** Add automatic homepage freshness marker from latest successful reindex timestamp

---

**Last Updated:** 2026-02-10 02:45:00 (America/Toronto)



