üß† Perimeter (The "Technical Source of Truth")
Purpose: A persistent repository for deep technical specifications following the Global Rules structure.

Structure:

üíª Env Specs
: Development vs. Deployment configurations
üåê Infra Ledger
: Network topology, connectivity investigations and resolutions
üìñ Magazine
: Dependencies, models, workflows, scripts commands and arguments
üêû Bug Log
: Dependency bugs, system incompatibility solutions
‚ö?Optimization
: GPU processes, memory utilization, code patterns
üåê Infra Ledger: Hybrid Network Topology (Phase C - 3-Node Setup)
Current Architecture Overview
As of 2026-02-10, the project uses a specific 3-node Hybrid Architecture:

1. Development Host (Norfolk): Windows 11 Dev Machine (192.168.2.131).
   - Role: Code editing, git management, deploying code to Instance via SSH/Rsync.
2. Control Plane (Huihuang): Local Server (192.168.2.130).
   - Role: Runs backend services (Temporal, MinIO, FastAPI) and Frontend Web UI.
   - Connectivity: Accessible internally via LAN. Exposed to Instance via Router Port Forwarding.
   - Services:
     - Web UI: http://192.168.2.130:3000/
     - MinIO Console: http://192.168.2.130:9001/
     - Temporal UI: http://192.168.2.130:8233/
3. Compute Plane (Instance): Vast.ai GPU Server (ssh2.vast.ai).
   - Role: Runs heavy compute tasks (Worker, Llama, Whisper).
   - Connectivity: Connected via SSH from Norfolk for management. Connects back to Huihuang for data/API access via public IP/Port Forwarding.

Service Distribution matrix
Service	Host	IP	Port	Role
Web (Next.js)	Huihuang	192.168.2.130	3000	User Interface.
FastAPI	Huihuang	192.168.2.130	8000	Backend API & Health.
Temporal Server	Huihuang	192.168.2.130	7233/8233	Workflow Orchestration.
MinIO Storage	Huihuang	192.168.2.130	9000	Object Storage (User: cres).
Temporal Worker	Instance (ssh2.vast.ai)	Remote	N/A	GPU Task Execution.
llama-server	Instance (ssh2.vast.ai)	Remote	8081	LLM Inference.
Development	Norfolk	192.168.2.131	N/A	Code & Deploy.

SSH Connectivity & Tunneling
- **Norfolk -> Instance**: `ssh -p 27139 root@ssh2.vast.ai -L 8080:localhost:8080`
  - Purpose: Mangement and forwarding llama-server (8081->8080) for debugging if needed.
- **Instance -> Huihuang**: Traffic routes through Router Port Forwarding (Public IP -> 192.168.2.130).
- **Norfolk -> Huihuang**: Direct LAN connection (User: `rama`).

Common Connectivity Issues (Phase C):

Issue	Cause	Resolution
API 502: fetch failed	FastAPI process on huihuang down	Restart FastAPI on LAN host.
No worker running	Worker process on Vast down	Run ./start_remote.sh --restart on Vast.
MinIO unreachable	LAN networking / Firewall issue	Check 192.168.2.130:9000 reachability.
Homepage unchanged	Index authority mismatch	Ensure generate_index.py writes to huihuang path.
Health Monitoring & Service Dependencies
FastAPI Health Check Endpoint
Endpoint: GET /health
File: 
src/api/main.py

Added: 2026-02-06 (Commit: 4f6289c)

Background
The /health endpoint provides comprehensive dependency verification for the multi-service architecture running in a single Docker container managed by supervisord. Unlike basic health checks that only verify the API is responding, this implementation actively probes all critical services to detect silent failures.

Purpose:

Enable load balancers/orchestrators to detect partial failures
Provide operational visibility into service health
Prevent routing traffic to containers with degraded dependencies
Support automated recovery workflows (e.g., supervisor restart triggers)
Architecture
The health check verifies 4 critical components:

Service	Port	Endpoint	Timeout
API	8000	N/A (self)	N/A
llama-server	8081	/health	2.0s
Temporal	8233	/api/v1/namespaces	2.0s
MinIO	9000	/minio/health/live	2.0s
Response Format
Healthy State (200 OK):

json
{
  "api": "ok",
  "llama": "ok",
  "temporal": "ok",
  "minio": "ok"
}
Degraded State (503 Service Unavailable):

json
{
  "api": "ok",
  "llama": "down",
  "temporal": "ok",
  "minio": "ok"
}
Status Codes:

200 OK - All services healthy
503 Service Unavailable - One or more services down
Implementation Details
Technology Stack:

FastAPI - Web framework
httpx - Async HTTP client (added in 
requirements.txt
)
JSONResponse - Custom response with dynamic status codes
Key Features:

Non-blocking checks - Uses async/await for concurrent probing
Timeout protection - 2-second timeout per check (prevents hanging)
Graceful degradation - Returns partial status even if checks fail
Exception safety - Catches all exceptions ‚Ü?marks service as "down"
Usage Examples
Command Line (curl)
bash
# Check all services
curl http://localhost:8000/health
# Check with verbose output
curl -v http://localhost:8000/health
# Use in scripts (exit code based on HTTP status)
if curl --fail http://localhost:8000/health; then
  echo "All services healthy"
else
  echo "Services degraded"
fi
Docker Health Check (docker-compose.yml)
yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s  # Allow time for llama model sync
Python (httpx)
python
import httpx
async def check_app_health():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8000/health")
        if resp.status_code == 200:
            print("‚ú?All services healthy")
        else:
            health = resp.json()
            down = [k for k, v in health.items() if v == "down"]
            print(f"‚ö†Ô∏è Services down: {', '.join(down)}")
Kubernetes Liveness Probe
yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 120  # Wait for model sync
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
Troubleshooting
Common Failure Scenarios:

Service	Common Causes	Resolution
llama: "down"	Model sync incomplete, GPU OOM	Check /var/log/llama.log, verify model file exists
temporal: "down"	Dev server crashed, DB corruption	Check /var/log/temporal.log, restart supervisor
minio: "down"	Port conflict, data directory locked	Check /var/log/minio.log, verify port 9000 available
Debugging Steps:

Check service logs: tail -f /var/log/<service>.log
Verify ports: netstat -tlnp | grep -E '8081|8233|9000'
Test endpoints directly:
bash
curl http://localhost:8081/health  # llama-server
curl http://localhost:8233/api/v1/namespaces  # Temporal
curl http://localhost:9000/minio/health/live  # MinIO
Performance Impact
Latency: ~50-200ms (concurrent checks with 2s timeout)
Resource: Minimal (async I/O, no CPU/memory overhead)
Recommendation: Poll every 30-60s (avoid excessive load)
Future Enhancements
Potential improvements:

Add worker process check (ps aux | grep worker)
Include disk space monitoring (warn at 80% usage)
Expose Prometheus metrics (/metrics endpoint)
Add startup probe (separate from liveness)
üìñ Magazine
Python Dependencies (requirements.txt)
File: 
requirements.txt

Last Updated: 2026-02-06

Package	Version	Purpose
yt-dlp	latest	YouTube video/metadata downloader
faster-whisper	latest	GPU-accelerated speech-to-text transcription
torch	cu121	PyTorch with CUDA 12.1 support (for faster-whisper)
numpy	latest	Numerical computing (torch dependency)
requests	latest	HTTP client for llama-server API calls
temporalio	latest	Temporal workflow orchestration SDK
fastapi	latest	Backend API framework
uvicorn	latest	ASGI server for FastAPI
httpx	latest	Async HTTP client for health checks
python-multipart	latest	Form data parsing for FastAPI
minio
latest	MinIO Python SDK for object storage
pypinyin	latest	Chinese pinyin conversion for workflow IDs
Critical Dependencies:

faster-whisper

GPU Acceleration: Requires CUDA runtime (uses torch with CUDA backend)
Model Storage: Downloads models to XDG_CACHE_HOME or ~/.cache/huggingface/
Memory: Base model ~140MB, runs in VRAM when device="cuda"
torch (CUDA 12.1)

Why cu121? Matches the CUDA version in the base image (ghcr.io/ggml-org/llama.cpp:server-cuda)
Index URL: https://download.pytorch.org/whl/cu121 (specified in requirements.txt)
Size: ~2GB download
temporalio

Worker Role: Executes activities (download, transcribe, summarize)
Client Role: API server uses client to start workflows
Server: Temporal dev server runs separately (installed via CLI, not pip)
Backend Data Processes
This section documents the core data pipelines orchestrated by Temporal.

Process	Package	Model	Device	Files
Video Search	yt-dlp	-	CPU	activities.py::search_videos
Video Download	yt-dlp	-	CPU	activities.py::download_video
Transcription	faster-whisper	Whisper Base	GPU	activities.py::transcribe_video
Summarization	llama-server	Llama-3.1-8B-Q4	GPU	
activities.py
, 
start-llama.sh
Keywords	llama-server	Llama-3.1-8B-Q4	GPU	activities.py::summarize_content
Indexing	MinIO SDK	-	CPU	
generate_index.py
Data Flow Architecture:

Search & Discovery: 
BatchProcessingWorkflow
 uses yt-dlp to find relevant videos based on a query. It filters by duration and live status.
Multimodal Extractions:
Audio: Extracted by yt-dlp and processed by faster-whisper (GPU backend) to generate a JSON transcript with timestamps.
Visuals: Thumbnails are fetched during download and stored in MinIO.
Semantic Enrichment: The llama-server (running Llama-3.1-8B) receives the transcript and generates a JSON blob containing a high-level summary and relevant keywords in the appropriate language (Chinese/English).
Vector/Index Synthesis: 
generate_index.py
 crawls the MinIO bucket, merges metadata, transcripts, and analysis, and produces the final 
web/src/data.json
 used by the Next.js frontend.
Model Paths (Remote):

Whisper: /workspace/packages/models/whisper (Downloaded on-demand/pre-cached)
Llama: /workspace/packages/models/llm (Managed by 
start-llama.sh
)
Workflow Orchestration & Function Call Relations
Temporal Workflows:

VideoProcessingWorkflow (
src/backend/workflows.py
)

Trigger: Single video URL submission via API
Activity Chain: 
download_video
 ‚Ü?
transcribe_video
 ‚Ü?
summarize_content
 ‚Ü?
refresh_index
Timeout: 30min (download) + 60min (transcribe) + 10min (summarize) + 2min (index)
Retry Policy: Download retries 3x, others single attempt
BatchProcessingWorkflow (
src/backend/workflows.py
)

Trigger: Keyword query submission
Activity Chain: 
search_videos
 ‚Ü?[Spawns N x 
VideoProcessingWorkflow
 as child workflows]
Parent Policy: ABANDON (children continue if parent terminates)
ID Format: batch-{pinyin_query} ‚Ü?video-{pinyin_query}-{video_id}
ReprocessVideoWorkflow (
src/backend/workflows.py
)

Trigger: Manual reprocessing via 
reprocess_keywords.py
Activity: 
summarize_content
 (re-runs LLM analysis)
Use Case: Update keywords/summaries after LLM model changes
Activity Dependencies:

API (FastAPI) 
  ‚Ü?(Temporal Client)
Temporal Server
  ‚Ü?(Task Queue: video-processing@cpu / video-processing@gpu)
Worker Process
  ‚îú‚îÄ download_video ‚Ü?MinIO (upload)
  ‚îú‚îÄ transcribe_video ‚Ü?GPU (faster-whisper) ‚Ü?MinIO (upload JSON)
  ‚îú‚îÄ summarize_content ‚Ü?llama-server:8081 ‚Ü?MinIO (update JSON)
  ‚îî‚îÄ refresh_index ‚Ü?generate_index.py ‚Ü?web/src/data.json
Scripts Commands & Arguments
Active Scripts (Used in production):

Script	Command	Key Arguments	Purpose
generate_index.py
python3 generate_index.py	None	Crawl MinIO and generate 
web/src/data.json
reprocess_keywords.py
python reprocess_keywords.py	None	Re-run LLM analysis on existing transcripts
connect_vast.py
python connect_vast.py	None	Establish SSH connection to Vast.ai
deploy_vast.py
python deploy_vast.py	None	Deploy codebase to remote instance
deploy_vast.sh
bash deploy_vast.sh	None	Alternative bash deployment script
start-llama.sh
bash start-llama.sh	Env vars: LLM_MODEL_PATH, LLAMA_THREADS	Start llama-server with model sync
Environment Variables:

LLM_MODEL_PATH: Path to LLM model directory (default: /workspace/packages/models/llm)
LLM_MODEL_FILE: Model filename (default: Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf)
LLAMA_THREADS: Thread count for inference (default: 8)
LLAMA_CTX_SIZE: Context window size (default: 4096)
LLAMA_NGL: GPU layer offload count (default: 999)
VAST_HOST, VAST_PORT, VAST_USER, VAST_SSH_KEY: SSH connection parameters
Supervisor Commands (Remote):

bash
# Service management
supervisorctl -c /etc/supervisor/supervisord.conf status
supervisorctl -c /etc/supervisor/supervisord.conf restart <service>
supervisorctl -c /etc/supervisor/supervisord.conf reload
# Service names: fastapi, llama, minio, temporal, worker, web
Scripts & Utilities [DELETED / LEGACY]
Script	Purpose	Key Functionality
debug_search.py	YouTube Search Debugger	Tests  yt-dlp search with default_search config.
debug_search_v2.py	Search Debugger (Prefix)	Improved search test using explicit ytsearch1: prefix.
setup_models.py	Whisper Model Setup	Pre-downloads the Whisper 
base
 model to the local cache.
setup_wsl.sh	WSL Environment Setup	Bash script to install Linux dependencies (FFmpeg, Python, Node).
test_demo.py	Batch Transcription Test	Transcribes all videos in test_downloads/ using VideoPipeline.
update_meta.py	Metadata Post-Processor	Generates summaries and keywords from transcript JSONs.
üíª Env Specs: Development vs. Deployment Configurations
Development Environment (Local Windows 11)
Platform:

OS: Windows 11 with Anaconda3
Python: 3.10+ (Anaconda base environment)
Node: 20.x LTS
IDE: VS Code with Antigravity extension
Development Workflow:

Code editing and testing on local machine
SSH tunneling to Vast.ai for remote service access
rsync for incremental code synchronization
Local 
.env
 file for SSH connection parameters
Key Tools:

connect_vast.py
: SSH connection manager
deploy_vast.py
/
deploy_vast.sh
: Deployment automation
Git for version control
Deployment Environment (Vast.ai RTX 3060)
Date: 2026-02-07 (Last Updated)

Hardware Profile:

GPU: 1x NVIDIA GeForce RTX 3060 (12GB VRAM)
CPU: 10 vCPUs
RAM: 11GB System RAM
Disk: 32GB SSD
Software Profile:

OS: Ubuntu 22.04 LTS (Jammy)
CUDA: 12.4
Driver: 550.163.01
Docker Base: ghcr.io/ggml-org/llama.cpp:server-cuda
Service Ports:

3000: Next.js Web UI
8000: FastAPI Backend
8081: llama-server
9000/9001: MinIO API/Console
7233/8233: Temporal API/UI
Resource Constraints & Tuning:

RAM Allocation: Max 7GB to background services (3GB llama + 4GB worker)
GPU Offloading: 999 layers to VRAM (-ngl 999)
Batch Size: 512 tokens (-b 512)
Thread Count: 8 (optimized for 10 vCPU)
üêû Bug Log: Docker & Runtime Fixes
1. Dockerfile Stage Inheritance (CRITICAL)
Issue: Final stage starting from a fresh BASE_IMAGE instead of the intermediate 
base
 stage.
Impact: All Python dependencies installed in the builder stage were LOST in the final image.
Fix: Changed final stage to FROM base.
2. .dockerignore Over-exclusion
Issue: Excluding the entire web/ directory.
Impact: frontend-builder could not find package.json or source files.
Fix: Refined to exclude only build artifacts (.next, node_modules).
3. PATH & Binary Resolution
Issue: Background services (uvicorn/npm) failing without absolute paths in 
supervisord.conf
.
Fix: Standardized to absolute paths (/usr/bin/npm, /usr/local/bin/uvicorn).
4. LLM Language Mismatch (Chinese ‚Ü?English)
Issue: Chinese transcripts generating English tags/summaries.
Impact: Tags like "AI", "GPT-4" instead of "‰∫∫Â∑•Êô∫ËÉΩ", "GPT-4" for Chinese videos.
Root Cause: Small LLM models (gemma-3-1b) have English bias; generic "same language" instruction insufficient.
Fix:
Added language detection (>30% Chinese characters).
Explicit "‰∏≠Êñá" instruction in prompt when Chinese detected.
Reduced temperature (0.7 ‚Ü?0.3) for consistency.
‚ö?Optimization: RTX 3060 VRAM Management
llama-server:
--n-batch 512: Optimized batch size for 12GB VRAM.
--memory-f32 false: Use FP16/K-Quant for KV cache to save memory.
RLIMIT_AS=4GB: Virtual memory limit (allows weights to be in VRAM while capping CPU side). Optimized to 3GB for 11GB RAM instances.
Temporal Worker:
RLIMIT_AS=6GB: Prevents worker from consuming remaining system RAM during parallel downloads. Optimized to 4GB for 11GB RAM instances.
## Infra Ledger Addendum (2026-02-10, Last 6 Hours, EST)

### Authoritative Runtime Placement
- `huihuang` (LAN server) remains control-plane owner:
  - Temporal server/UI
  - MinIO API/Console
  - FastAPI
  - Next.js Web
- Vast instance remains compute-plane owner:
  - Temporal worker process(es)
  - llama.cpp service
  - whisper/faster-whisper runtime

### Execution Convention
- Do not use WSL for this project's operational commands.
- Use Conda environments on Norfolk/huihuang as the standard operator shell.

### Data/Combine Limit Policy (Current)
- API/page fetch path no longer capped at 5 by default.
- Current transcriptions/sentence fetch defaults and max are 50 (bounded).
- Practical combine count equals returned result count, subject to available query-matched videos and downstream processing capacity.

### Queue/Worker Identity Convention (Target)
- Desired worker IDs:
  - CPU queue worker: `<host>@cpu`
  - GPU queue worker: `<host>@gpu`
- Avoid suffix chaining patterns like `@gpu@cpuq`.

### Operations Guardrails
- Instance should not run local Temporal/MinIO when externalized to huihuang.
- After host reboot, check in order:
  1. Temporal reachable from worker
  2. MinIO credentials valid
  3. FastAPI upstream reachable
  4. Worker queue registration healthy

### Release Tags & CI Guardrails (2026-02-10 Addendum)
- GHCR app image tags:
  - `:canary` = current change stream
  - `:stable` = validated promotion
- Promotion method:
  - manual `workflow_dispatch` in `.github/workflows/deploy.yml`
  - set `promote_stable=true` after canary verification
- CI minimal runtime check:
  - `.github/workflows/ci-minimal-image.yml`
  - builds base/app images, boots container with externalized control-plane deps, runs `scripts/container_smoke.sh`

### Worker Startup Mode (Current)
- Supervisord programs:
  - `worker-cpu` (`autostart=false`)
  - `worker-gpu` (`autostart=false`)
- Worker boot is demand-driven by scheduler/API trigger path where supervisor is colocated.



## 2026-02-12 Addendum - Legacy Deploy Script Retirement (Current Policy)

- `deploy_vast.sh` and `deploy_vast.py` are retired from active operations.
- Archived copies:
  - `scripts/archive/legacy_deploy_vast.sh`
  - `scripts/archive/legacy_deploy_vast.py`
- Root files now act as deprecation stubs and must not be used for deployment.
- Current one-way flow is mandatory: `huihuang/GitHub -> GHCR -> Vast instance`.
- Production `docker run` ownership is Vast.ai runtime configuration; CI `docker run` is only for smoke validation.
- For incident handling, use `docs/vast_deployment.md` as the active runbook.
