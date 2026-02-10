# Vast.ai Deployment Guide

## Prerequisites

1.  **Vast.ai Account**: Sign up and add credits.
2.  **SSH Key**: Ensure you have an SSH key pair (e.g., `~/.ssh/id_rsa`). Add the public key to your Vast.ai account.
3.  **Vast CLI** (Optional): Useful for searching instances via command line.

## Renting an Instance

We recommend an instance with:
-   **GPU**: RTX 3090 or 4090 (24GB VRAM) recommended for optimal LLM performance.
-   **Image**: `ghcr.io/ggml-org/llama.cpp:server-cuda`
    -   *Why?* This image comes with pre-compiled `llama.cpp` server with CUDA support, which this project relies on.
-   **Disk Space**: At least 50GB (models are large).

## Configuration

1.  Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
2.  Fill in your instance details from the Vast.ai console:
    -   `VAST_HOST`: The SSH hostname (e.g., `ssh4.vast.ai`).
    -   `VAST_PORT`: The SSH port mapping (e.g., `34567`).
    -   `VAST_SSH_KEY`: Absolute path to your private key (e.g., `/home/user/.ssh/id_rsa`).

## Deployment

Run the deployment script:
```bash
./deploy_vast.sh
```

### What `deploy_vast.sh` does:
1.  **Syncs Code**: Uses `rsync` to upload the current directory to `/workspace` on the remote instance.
2.  **Uses Prebuilt Image Runtime**: The instance image already contains runtime dependencies.
3.  **Starts Services**: Launches supervisord-managed services (FastAPI, CPU/GPU workers, llama; web disabled by default in hybrid mode).

## Instance Dependency Policy

The instance image must install runtime dependencies at build time from:

- `requirements.instance.txt`

Do **not** rely on post-deploy `pip install` for normal startup.  
`requirements.txt` may still be used for local/full development, but instance runtime should stay on the minimal/validated set in `requirements.instance.txt`.

## GHCR Tag Policy

- `:canary` = default publish target for current changes
- `:stable` = manual promotion tag (only when explicitly requested/validated)

### Promotion Workflow (Recommended)

1. Trigger `Build and Push to GHCR` with default options.
2. Validate `:canary` on target instance (health, queues, one batch run).
3. Re-trigger workflow with `promote_stable=true` to publish `:stable`.

### Runtime Startup Policy

- Image startup is supervisord-driven.
- `fastapi` autostarts.
- `worker-cpu` and `worker-gpu` are configured as **on-demand** (`autostart=false`).
- Workers are started by scheduler-trigger path (`/batch`/`/process`) via best-effort `supervisorctl start worker-cpu/worker-gpu` when colocated.

### CI Guardrail

Minimal image boot validation is enforced in CI via:

- `.github/workflows/ci-minimal-image.yml`

It builds base + app image, starts Temporal/MinIO test dependencies, boots app container, and runs `scripts/container_smoke.sh`.

## Verification

Access the services via SSH tunneling or opened ports (if configured):
-   **Web UI**: Port 3000
-   **MinIO Console**: Port 9001
-   **FastAPI Docs**: Port 8000/docs
