# Tasks

## 2026-02-12 (Thursday)
### Control Plane (Temporal / MinIO / Web / Control API)
- [ ] Implement `web/src/app/audio/page.tsx` to add `/audio` route with server-side data loading from existing `data.json` source.
- [ ] Implement `web/src/app/audio/AudioClient.tsx` for audio-focused list/filter UI without changing existing `/video` behavior.
- [ ] Implement homepage navigation entry in `web/src/app/page.tsx` to expose the new `Audio` page.
- [ ] Configure styles in `web/src/app/globals.css` for audio page layout using existing design tokens.

### Docs & Ops (Runbook / Validation / Architecture)
- [ ] Verify `npm run build` in `web/` passes after adding the new route.
- [ ] Test `/audio` page manually on `http://127.0.0.1:3000/audio` and confirm links/playback fall back gracefully when media is missing.
- [ ] Document rollout and rollback steps for the audio page in `docs/PLAN.md` only if API contract or ops behavior changes.
- [x] Fix committed secret exposure in `scripts/supervisord_remote.conf` by switching to runtime env interpolation.
- [x] Document queue/runtime/security alignment and rollback in `docs/PLAN.md`.

### Workers & Queues (@cpu / @gpu)
- [x] Fix queue routing names to `<base>@cpu` and `<base>@gpu` in `src/api/main.py`, `src/backend/workflows.py`, and `src/backend/worker.py`.
- [x] Fix queue references in operational scripts (`scripts/container_smoke.sh`, `scripts/rerun_failed_workflows.py`) to use the new suffix routing.
- [ ] Verify worker pollers register on `video-processing@cpu` and `video-processing@gpu` after restart.

### Resource & Performance (RAM / VRAM / Batch / Threads)
- [x] Fix runtime defaults for llama to `-ngl 999 --threads 8 -b 512` in `entrypoint.sh` and `start_llm.sh`.
- [x] Fix worker/llama memory caps in `scripts/supervisord_remote.conf` to align with triage baseline (`4GB` workers / `3GB` llama).
- [x] Implement active-instance scheduling caps in `src/api/main.py` (`SCHEDULER_ACTIVE_INSTANCE`, `SCHEDULER_ACTIVE_MAX_PARALLELISM`).
- [ ] Test batch scheduling throughput on active instance and tune `SCHEDULER_ACTIVE_MAX_PARALLELISM` if instance profile changes.

### Networking & NAT (64.229.113.233 / Port Forwarding)
- [x] Fix `.env.example` control-plane endpoints to current NAT/public defaults (`64.229.113.233`).

## 2026-02-11 (Wednesday)
### Docs & Ops (Runbook / Validation / Architecture)
- [x] Document canonical project root as `C:\Users\rama\cres_ytdlp_norfolk` and archive path at `C:\Users\rama\_archive\legacy_root_project_20260211_215608`.
- [x] Verify web service responds at `http://127.0.0.1:3000` after launcher restart.
- [x] Verify ports `3000` (web) and `8000` (FastAPI) are listening.
- [x] Document rollback runbook for restoring archived root copy and rerunning launchers.

## 2026-02-10 (Tuesday)
### Control Plane (Temporal / MinIO / Web / Control API)
- [x] Implement transcriptions API limit increase from `5` to `50` in `src/api/routers/transcriptions.py`.
- [x] Implement frontend query limit alignment in `web/src/app/transcriptions/page.tsx` and `web/src/app/sentence/page.tsx`.
- [x] Implement Next API proxy default limit update to `50` in `web/src/app/api/transcriptions/route.ts`.
- [x] Implement transcriptions UI text update from `max 5` to `max 50` in `web/src/app/transcriptions/TranscriptionsClient.tsx`.
- [ ] Verify playback/UI smoke and workflow throughput after limit expansion.

### Docs & Ops (Runbook / Validation / Architecture)
- [x] Document runtime rule to avoid WSL and prefer Conda on Norfolk/huihuang.
- [x] Document architecture rule that control plane runs on huihuang and compute runs on Vast.ai GPU instance.
- [ ] Document and keep instance-local Temporal/MinIO disabled for the current topology.
- [ ] Document hybrid runtime migration summary and artifact status update.

### Networking & NAT (64.229.113.233 / Port Forwarding)
- [ ] Configure SSH configs for Vast.ai and huihuang with current host/IP values.
- [ ] Verify connectivity to both hosts after SSH config updates.
- [ ] Document latest IP/port mapping in perimeter/runbook docs.

### Workers & Queues (@cpu / @gpu)
- [ ] Verify Temporal monitoring results for 30 workflows (`turbo-all`).
- [ ] Verify MinIO artifacts exist for newly produced videos (`turbo-all`).
- [ ] Verify `data.json` refresh on huihuang after workflow completion.
- [ ] Deploy codebase (including `start_remote.sh`) to Vast.ai instance and verify worker restart behavior.

## 2026-02-06 (Thursday)
### Networking & NAT (64.229.113.233 / Port Forwarding)
- [ ] Configure SSH tunnel with port `8080` forwarding.
- [ ] Deploy local codebase sync to remote `/workspace/`.
- [ ] Verify remote service behavior after sync.

### GPU Instance (llama / Whisper / Compute API)
- [ ] Implement GPU-accelerated video decoding (FFmpeg NVDEC).

### Control Plane (Temporal / MinIO / Web / Control API)
- [ ] Implement transcriptions page combined section + carousel follow-up.
- [ ] Test transcriptions backend endpoint with `curl`.
- [ ] Verify carousel navigation and combined keyword rendering.

### Docs & Ops (Runbook / Validation / Architecture)
- [ ] Document cookies upload requirement to unblock restricted downloads.
- [ ] Deploy re-trigger of failed "Oracle" workflows.
- [ ] Verify successful download and transcription for retried Oracle workflows.
- [x] Document migration of legacy ledger items into structured Task.md sections.
