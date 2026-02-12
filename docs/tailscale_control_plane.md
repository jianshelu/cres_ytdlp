# Vast.ai with External Control Plane (Tailscale)

## Goal
- Run app services on vast.ai (`llama`, `fastapi`, `worker`, `web`).
- Keep Temporal/MinIO tools in image as backup capability.
- Use LAN control plane over Tailscale in normal mode:
  - Temporal: `100.121.250.72:7233`
  - MinIO: `http://100.121.250.72:9000`

## Modes
- `CONTROL_PLANE_MODE=external` (default):
  - Instance joins Tailscale.
  - App connects to external Temporal/MinIO.
  - No local Temporal/MinIO start.
- `CONTROL_PLANE_MODE=local` (rollback):
  - Instance starts local Temporal/MinIO (if binaries installed).
  - Used when LAN control plane is unavailable.

## Required env vars
- `TEMPORAL_ADDRESS=100.121.250.72:7233`
- `MINIO_ENDPOINT=100.121.250.72:9000`
- `MINIO_SECURE=false`
- `MINIO_ACCESS_KEY=...`
- `MINIO_SECRET_KEY=...`
- Optional: `TAILSCALE_AUTHKEY=...`

## Deploy
1. Copy `.env.example` to `.env` and fill values.
2. Run `./deploy_vast.sh`.
3. Check status on instance: `./start_remote.sh --status`.

## Rollback strategy (image + mode)
1. Backup current GHCR image:
   - `GHCR_IMAGE=ghcr.io/jianshelu/cres_ytdlp:latest ./scripts/backup_ghcr_image.sh`
2. Build policy:
   - Primary image (recommended): `INCLUDE_LOCAL_CONTROL_PLANE=true` (default, keep embedded Temporal/MinIO tools).
   - Optional slim image: `INCLUDE_LOCAL_CONTROL_PLANE=false`.
   - Example:
     - `docker build -f Dockerfile.base --build-arg INCLUDE_LOCAL_CONTROL_PLANE=true -t ghcr.io/jianshelu/cres_ytdlp-base:latest .`
     - `docker build -f Dockerfile.base --build-arg INCLUDE_LOCAL_CONTROL_PLANE=false -t ghcr.io/jianshelu/cres_ytdlp-base:slim-external .`
     - push both tags to GHCR.
3. If external control plane fails:
   - Set `CONTROL_PLANE_MODE=local` and redeploy.
4. If needed, switch image to backup tag:
   - `ghcr.io/jianshelu/cres_ytdlp:legacy-control-plane-latest`.
