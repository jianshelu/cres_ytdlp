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
2.  **Installs Dependencies**: Installs Python and Node.js packages.
3.  **Starts Services**: Launches MinIO, Temporal, FastAPI, and Next.js in the background.

## Verification

Access the services via SSH tunneling or opened ports (if configured):
-   **Web UI**: Port 3000
-   **MinIO Console**: Port 9001
-   **FastAPI Docs**: Port 8000/docs
