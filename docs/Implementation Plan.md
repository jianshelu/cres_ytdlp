📋 GLOBAL RULES: ARCHITECTURAL STATE & TEMPORAL MANAGEMENT 🚀
Date 📅	Models/Systems ⚙️	Threads 🧵	Status 🚦	Completion Time ⏱️
2026-02-10	Infrastructure	Migration Explanation	[IN-PROGRESS]	-
2026-02-06	Script Analysis	Analyzing Scripts	[DONE]	19:25:00
2026-02-06	Project Cleanup	Archive Deletion	[DONE]	20:05:00
2026-02-06	Workspace Rules	Rule Reintegration	[DONE]	20:16:00
2026-02-06	Deployment Config	Health Check & Resource Limits	[DONE]	21:14:00
2026-02-06	Docker Fixes	Production Ready Dockerfile	[DONE]	23:45:00
2026-02-06	LLM Fixes	Chinese Language Tag Generation	[DONE]	23:55:00
2026-02-07	UI Enhancement	Transcription Player Improvements	[DONE]	00:15:00
2026-02-07	Docker Fix	Build Disk Space Cleanup	[DONE]	00:25:00
2026-02-07	Feature Fix	Tag-To-Video Jump (Minus 1s)	[DONE]	00:50:00
2026-02-07	Deployment	Verify & Rebuild Remote UI	[DONE]	00:45:00
2026-02-07	UI Refinement	Restore Karaoke Effect & Full Length	[DONE]	01:00:00
2026-02-07	Infrastructure	Docker Image Size Analysis	[DONE]	01:15:00
2026-02-07	Infrastructure	Update SSH Connect Scripts	[DONE]	01:25:00
2026-02-07	Infrastructure	Instance Recovery (IP/Port Change)	[DONE]	23:33:00
2026-02-07	Debugging	Frontend Video Display & Workflow Recovery	[DONE]	01:55:00
2026-02-07	UI Feature	Transcription Search UI (Sidebar + Comparison Page)	[DONE]	20:57:00
2026-02-07	LLM Feature	Combined Keywords with Carousel Layout	[IN-PROGRESS]	-
2026-02-07	Debugging	Fix Failed "Oracle" Workflows (yt-dlp Cookies)	[IN-PROGRESS]	-
Date: 2026-02-06 // Script Analysis & Project Cleanup
🧵 Plan 1: "Script Documentation"

Context: The user requested an explanation of the scripts in the scripts path.
Outcome: Comprehensive understanding and documentation of each utility script.
Strategy:
Read all script files in scripts/ directory.
Document each script's purpose, key functionality, and dependencies.
Add to Perimeter Magazine section for technical reference.
Scope: scripts/debug_search.py, debug_search_v2.py, setup_models.py, setup_wsl.sh, test_demo.py, update_meta.py.
🧵 Plan 2: "Cleanup & Archival"

Context: User confirmed these scripts are abandoned for structural cleanup.
Outcome: Clean project root and organized legacy storage.
Strategy:
Move all files from scripts/ to archive/scripts/.
Commit the move operation.
Update Perimeter to mark scripts as [DELETED/LEGACY].
Scope: scripts/ → archive/scripts/ (6 files).
🧵 Plan 3: "Permanent Deletion of Legacy Code"

Context: User confirmed the archive/ folder is dead code and should be removed.
Outcome: Minimalist project tree without legacy clutter.
Strategy:
Delete entire archive/ directory recursively.
Stage deletion with git rm -rf archive/.
Commit with descriptive message.
Scope: archive/ folder (containing scripts/ subdirectory).
🧵 Plan 4: "Restore & Commit Workspace Rules"

Context: User clarified the project version of rules is correct and should be tracked.
Outcome: Workspace Rules are officially part of the codebase.
Strategy:
Restore original 
.agent/rules/workwithvastai.md
 content.
Remove .agent/rules/ from .gitignore.
Stage and commit to make rules part of version control.
Scope: .agent/rules/workwithvastai.md, .gitignore.
🧵 Plan 5: "Health Check Implementation"

Context: Production readiness requires comprehensive service health monitoring.
Outcome: /health endpoint verifying all critical dependencies.
Strategy:
Add /health endpoint to src/api/main.py using httpx.
Check llama-server (port 8081), Temporal (8233), MinIO (9000).
Return 200 if all healthy, 503 if any service down.
Add httpx to requirements.txt.
Scope: src/api/main.py, requirements.txt.
🧵 Plan 6: "Tuning for 11GB RAM Instance"

Context: The actual Vast.ai instance has 11GB RAM and 10 CPUs, which is tighter than the previous assumption.
Outcome: Configs optimized for low system RAM while maximizing GPU/CPU usage.
Strategy:
Set llama RLIMIT_AS=4GB (weights in VRAM).
Set worker RLIMIT_AS=6GB (prevent OOM).
Update LLAMA_THREADS=10 to match CPU count.
Add --n-batch 512 --memory-f32 false for RTX 3060.
Scope: scripts/supervisord.conf, scripts/start-llama.sh.
🧵 Plan 7: "Restore Full Project Structure in Docker"

Context: Selective COPY was excluding root scripts (onstart.sh, reprocess_keywords.py, etc.) causing user concern and startup failures.
Outcome: Full project structure preserved in /workspace within the image.
Strategy:
Create .dockerignore excluding .git, __pycache__, .next, node_modules.
Change Dockerfile from selective COPY to inclusive COPY . ./.
Verify all root scripts present in built image.
Scope: Dockerfile, .dockerignore.
🧵 Plan 8: "Fix Docker Production Deployment"

Context: Image built on GHCR was missing Python packages and had PATH issues on Vast.ai.
Outcome: Robust, self-contained Docker image running all services healthy with all dependencies.
Strategy:
Stage 1 (base): Install requirements.txt packages (yt-dlp, temporalio, fastapi, etc.) via pip.
Stage 2 (frontend-builder): Build Next.js frontend.
Stage 3 (final): Inherit from base (CRITICAL FIX: was FROM ${BASE_IMAGE}, now FROM base).
Update .dockerignore to allow web source while excluding build artifacts.
Use absolute paths in supervisord.conf.
Scope: Dockerfile (3-stage build), .dockerignore, supervisord.conf, requirements.txt.
🧵 Plan 9: "Fix Chinese Language Tag Generation"

Context: Chinese videos were generating English tags instead of Chinese (e.g., "AI" instead of "人工智能").
Outcome: LLM generates summary and keywords in the same language as the input transcript.
Strategy:
Add language detection (Chinese character percentage).
Strengthen prompt with explicit "中文" instruction when Chinese detected.
Lower temperature (0.7 → 0.3) for consistent language matching.
Scope: src/backend/activities.py (summarize_content activity).
Date: 2026-02-07 // UI Enhancement & Feature Fixes
🧵 Plan 10: "Enhance Video Page Transcription UI"

Context: User wants full transcription display below video with paragraph layout and word-level interaction.
Outcome: Interactive paragraph-style transcription with sticky video.
Strategy:
Paragraph Layout: Render segments as continuous flow of interactive word spans.
Word Seeking: Use linear interpolation for word-level timestamps.
Sticky Video: Update CSS to pin video player at top.
Scope: KaraokeTranscript.tsx, globals.css.
🧵 Plan 11: "Fix Docker Build Disk Space Exhaustion"

Context: GHCR build failing due to large Triton/PyTorch artifacts filling disk.
Outcome: Optimized build process using single-layer cleanup.
Strategy:
Add rm -rf /root/.cache/pip.
Remove Python bytecode from dist-packages.
Scope: Dockerfile.
🧵 Plan 12: "Fix Tag-To-Video Jump Feature"

Context: Keyword tags on home page should jump to first occurrence in video minus 1 second.
Outcome: Reliable tag-based seeking across the app.
Strategy:
Regex Matching: Update generate_index.py with re.search(rf'\b{word}\b') for precise start_time index.
Seek Calculation: Use Math.max(0, start_time - 1) in VideoCard.tsx.
Scope: generate_index.py, VideoCard.tsx.
🧵 Plan 13: "Verify & Rebuild Remote UI"

Context: Manual SCP transfers need a remote npm run build to become live in production.
Outcome: Frontend changes fully deployed to instance.
Strategy:
Confirm connectivity post-reboot.
Execute remote build and supervisor restart.
Scope: Remote Instance.
Date: 2026-02-07 // UI Refinement & GPU Performance
🧵 Plan 14: "Restore Karaoke Effect & Full Length Display"

Context: Interactive paragraph layout was less intuitive. User requested sentence-per-line Karaoke display with segment highlighting.
Outcome: Classic Karaoke UI with active segment bolding and full-depth display.
Strategy:
Refactor KaraokeTranscript.tsx to vertical list.
Add active-segment CSS animations and colors.
Force full container height in globals.css.
Scope: KaraokeTranscript.tsx, globals.css.
🧵 Plan 15: "Implement GPU-Accelerated Video Decoding"

Context: Transcription and downloading are currently bottlenecked by CPU-only FFmpeg.
Outcome: 2x-5x speedup in audio extraction and video merging.
Strategy:
Add specialized FFmpeg build (NVIDIA/CUVID) to Dockerfile.base.
Passing --prefer-free-formats and hardware flags to yt-dlp.
Verify with ffmpeg -decoders | grep h264_cuvid.
Scope: Dockerfile.base, src/backend/activities.py.
🧵 Plan 16: "Frontend Display & Workflow Recovery"

Context: Videos are not appearing on the site despite data.json existance. Workflow gNHY1UR_2rU failed due to live stream detection.
Outcome: Working frontend display and resolution for the failed workflow.
Strategy:
Check web and fastapi logs for path or connectivity errors.
Verify data.json location and content vs. frontend expectations.
Optimize RLIMIT_AS for 11GB RAM (Current: ~10GB total is too tight).
Re-run generate_index.py on remote to ensure index is fresh.
Investigate bypassing is_live check for specific archived streams.
Scope: web/, src/backend/activities.py, scripts/supervisord.conf.
🧵 Plan 17: "Transcription Search UI (Sidebar + Comparison Page)"

Context: User requests a keyword sidebar on the frontpage and a new transcription comparison page.
Outcome:
Frontpage displays keyword sidebar on the right side
Clicking a keyword navigates to /transcriptions?keyword=X
Transcription page shows all videos containing that keyword side by side
Each video card shows: highlighted keyword sentence + full transcript below
Strategy:
Frontend Layout Change (page.tsx): Convert to 2-column layout (videos left, keyword sidebar right)
Keyword Aggregation: Extract unique keywords from all videos' data.json for sidebar
New Route (/transcriptions/page.tsx): Server component that filters videos by keyword
Comparison Component (TranscriptionCard.tsx): Displays title, highlighted sentence, and full transcript
CSS Updates (globals.css): Sidebar styling, comparison grid, keyword highlight
Scope:
[MODIFY] web/src/app/page.tsx - Two-column layout with keyword sidebar
[NEW] web/src/app/transcriptions/page.tsx - Transcription comparison page
[NEW] web/src/app/components/TranscriptionCard.tsx - Card component with highlight
[MODIFY] web/src/app/globals.css - Sidebar and comparison styles
Verification:
npm run build - Ensure no TypeScript errors
Browser test: Click keyword in sidebar → verify navigation
Verify multiple transcriptions render side by side with correct highlighting
🧵 Plan 18: "Combined Keywords Feature (LLM + Carousel)"

Context: Enhance transcription search with LLM-powered keyword extraction across multiple videos and carousel UI.
Outcome:
Use Meta-Llama-3.1-8B to extract semantically relevant keywords in real-time
Generate 5 "combined keywords" from all transcriptions with coverage compensation
Extract and merge sentences containing combined keywords into "combined sentence"
Display transcriptions in a carousel/slideshow instead of crowded 5-column layout
Strategy:
Backend API (src/backend/routers/transcriptions.py):
New endpoint GET /api/transcriptions?query={query}&limit=5
Integrate with llama.cpp HTTP server for keyword extraction
Call LLM twice: (a) 50 candidates from combined text, (b) 30 candidates per video
Keyword Service (src/backend/services/keyword_service.py):
LLM provides semantic scores (0-1 range)
Program calculates occurrence counts from actual text
Sort by: Score DESC → Count DESC → term ASC
Coverage compensation algorithm (max 3 replacements, protect top 2 core terms)
Combined Sentence (src/backend/services/sentence_service.py):
Split combined transcription into sentences
Extract first sentence containing each of 5 combined keywords
Deduplicate and merge into single paragraph
Frontend Carousel (web/src/app/transcriptions/page.tsx):
Top section: Search word badge + 5 combined keyword tags + combined sentence (collapsible)
Main section: Carousel showing 1 transcription at a time with prev/next controls
Each slide shows: video title, per-video keyword tags, scrollable transcript
Frontpage Layout Fix (web/src/app/page.tsx):
Revert video grid from 2-column to 3-column (as per spec)
Keep keyword sidebar on right
CSS (web/src/app/globals.css):
Carousel container with slide transitions
Combined keywords tag styling with score-based colors
Combined sentence box styling
Scope:
[NEW] src/backend/routers/transcriptions.py - FastAPI aggregation endpoint
[NEW] src/backend/services/keyword_service.py - LLM integration + coverage algorithm
[NEW] src/backend/services/sentence_service.py - Combined sentence extraction
[NEW] src/backend/services/llm_llamacpp.py - llama.cpp HTTP client
[MODIFY] web/src/app/page.tsx - Change grid from 2-column to 3-column
[MODIFY] web/src/app/transcriptions/page.tsx - Add combined section + carousel
[NEW] web/src/app/components/TranscriptionCarousel.tsx - Carousel component
[MODIFY] web/src/app/globals.css - Carousel + combined content styling
Verification:
Backend: curl /api/transcriptions?query=Gemini&limit=5 returns valid JSON with combined keywords
LLM validation: Combined keywords have semantic relevance scores, counts match actual text
Coverage check: Each of 5 videos should be represented in combined keywords (within MAX_REPLACE constraint)
Frontend: Carousel navigation works smoothly with keyboard arrows and click controls
Combined sentence contains only original sentences from transcripts (no hallucinated text)
🧵 Plan 19: "Fix Failed 'Oracle' Workflows (yt-dlp Cookies)"

Context: "Oracle" search workflows are failing because yt-dlp is blocked by YouTube's bot detection, requiring cookies.
Outcome: Continued automation of video discovery even when facing bot detection.
Strategy:
Activity Update (src/backend/activities.py):
In download_video and search_videos, check for os.path.exists("/workspace/cookies.txt").
If exists, add 'cookiefile': '/workspace/cookies.txt' to ydl_opts.
User Notification: Request user to export Netscape format cookies from their browser and upload to /workspace/cookies.txt on the remote instance.
Verification: Manually re-trigger batch-Oracle or individual video workflows.
Scope:
[MODIFY] src/backend/activities.py - Add cookiefile support
[ACTION] User uploads cookies.txt to Vast.ai
Verification:
Run temporal workflow list and verify new Oracle workflows complete.
Check worker.log for successful downloads.
## Date: 2026-02-10 // Incremental Plan Update (Last 6 Hours, EST)

Plan Statement
Consolidate the latest runtime/ops decisions into docs while keeping architecture authoritative and executable across Norfolk, huihuang, and Vast instance.

Scope
1. Keep control plane on `huihuang` (Temporal/MinIO/Web/FastAPI) and compute on Vast instance (worker + llama/whisper).
2. Remove hardcoded 5-video cap in transcriptions/sentence data fetch path.
3. Standardize execution preference: Conda on Norfolk/huihuang, avoid WSL usage.
4. Validate instance cleanup direction (no local Temporal/MinIO service ownership on instance for current topology).

Execution Notes
- Backend transcriptions API limit ceiling updated from 5 to 50.
- Frontend transcriptions/sentence pages no longer hardcode limit 5; now bounded and default to 50.
- API proxy default limit updated to 50.
- UI label updated from `max 5` to `max 50`.

Verification Plan
1. Query path: `/api/transcriptions?query=<q>&limit=20` returns up to 20 items when data exists.
2. UI path: `transcriptions` and `sentence` pages reflect fetched count >5.
3. Runtime path: worker remains on instance; control-plane services remain on huihuang.

Risks / Follow-ups
- Large limit values increase LLM/extraction latency and payload size.
- If workflow-level combine still uses legacy caps elsewhere, continue follow-up in activity/workflow layer.
