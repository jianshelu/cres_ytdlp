# Hybrid Runtime Migration Summary (LAN Control Plane + Vast GPU Worker)

## 1. Purpose

This document is the single runbook for:
- architecture migration history,
- current service ownership,
- service access patterns,
- startup/monitoring commands,
- troubleshooting and rollback.

Time zone reference: `America/Toronto`.

---

## 2. Migration Overview

### Phase A: Single-host on Vast.ai (initial)
- Web, FastAPI, Worker, llama.cpp, Temporal, MinIO were all started on instance.
- Pros: simple to bootstrap.
- Cons: control-plane and object storage were tied to ephemeral GPU instance lifecycle.

### Phase B: External control plane via Tailscale (intermediate)
- Temporal/MinIO moved out of instance.
- Instance connected through Tailscale.
- This phase is now retired.

### Phase C: Public forwarding + LAN-hosted control plane/web (current)
- Control-plane and user-facing services moved to LAN host `huihuang`.
- Instance is focused on GPU-heavy execution.
- Tailscale removed from active path.

---

## 3. Current Architecture (Authoritative)

### 3.1 Service ownership

| Service | Host | Port | Role |
| :--- | :--- | :--- | :--- |
| Web (Next.js) | `huihuang` (`192.168.2.130`) | `3000` | User UI |
| FastAPI | `huihuang` (`192.168.2.130`) | `8000` | API entry (`/batch`, `/health`, admin/reindex) |
| Temporal | `huihuang` | `8233` (UI), `7233` (gRPC) | Workflow control plane |
| MinIO | `huihuang` | `9000` (S3/API), `9001` (console if enabled) | Object storage |
| Worker (Temporal) | Vast instance | internal process | Activity execution |
| llama.cpp | Vast instance | `8081` | LLM inference |
| Whisper/faster-whisper | Vast instance | library/runtime | GPU transcription |

### 3.2 Host responsibilities

- `huihuang` is the control and presentation plane.
- Vast instance is the compute plane for GPU-heavy pipeline tasks.
- `web/src/data.json` used by production web should be generated/updated on the web host authority path, not assumed from developer machine snapshots.

---

## 4. Service Access Methods

## 4.1 LAN access (Norfolk <-> huihuang)

No SSH tunnel required when both hosts are in the same LAN and routing/firewall allow access.

- Web: `http://192.168.2.130:3000`
- FastAPI docs: `http://192.168.2.130:8000/docs`
- FastAPI health: `http://192.168.2.130:8000/health`
- Temporal UI: `http://192.168.2.130:8233`
- MinIO API health: `http://192.168.2.130:9000/minio/health/live`

## 4.2 Vast instance access

Instance management still uses SSH tunnel/SSH login. Example pattern:

```bash
ssh -p <VAST_PORT> root@<VAST_HOST> -L 8080:localhost:8080
```

This tunnel is for instance service debugging (for example llama local port), not for routing LAN web/API traffic by default.

## 4.3 Public forwarding path (if enabled)

When router forwarding is configured, instance may reach LAN control plane via public endpoint.
Use this only when direct LAN/private routing is unavailable.

---

## 5. Required Runtime Configuration

Important variables for worker/API interoperability:

- `TEMPORAL_ADDRESS`
- `MINIO_ENDPOINT`
- `MINIO_SECURE`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `REINDEX_URL`

Current scripts also include defaults in:
- `entrypoint.sh`
- `start_remote.sh`

If topology changes, update these values first, then restart services.

Instance image dependency source:
- Use `requirements.instance.txt` for build-time runtime dependencies.
- Avoid post-deploy `pip install` as part of normal operations.

---

## 6. Startup and Monitoring

## 6.1 Vast instance (worker + llama + optional API/web in fallback)

```bash
cd /workspace
./start_remote.sh --restart
./start_remote.sh --status
```

Quick checks:
- FastAPI (if running on instance): `curl -i http://127.0.0.1:8000/health`
- Worker logs: `/var/log/worker.log`
- API logs: `/var/log/fastapi.log`
- Combined app logs: `/workspace/logs/app.log`

## 6.2 huihuang host

Keep these services auto-started (Task Scheduler/service wrappers):
- Temporal (`7233/8233`)
- MinIO (`9000`, data path on `D:\minio-data`)
- Web (`3000`)
- FastAPI (`8000`)

---

## 7. Data and Request Flow

1. User submits query from Web (`huihuang:3000`).
2. Web API proxy forwards to FastAPI (`huihuang:8000/batch`).
3. FastAPI starts Temporal workflow in control plane (`huihuang:7233`).
4. Worker on instance polls Temporal queue and executes:
   - `search_videos` -> `download_video` -> `transcribe_video` -> `summarize_content` -> `build_batch_combined_output`.
5. Artifacts are written to MinIO (`huihuang:9000`).
6. Reindex callback updates homepage index (`REINDEX_URL`).
7. Web displays updated results.

---

## 8. Known Failure Patterns and Fixes

## 8.1 `API 502: Failed to parse URL from http://127.0.0.1:8000 /batch`
Cause:
- malformed backend URL (extra space or invalid concatenation).

Fix:
- normalize API URL, trim whitespace, remove trailing slash issues.
- verify frontend proxy route builds `${API_URL}/batch` correctly.

## 8.2 `API 502: fetch failed`
Cause:
- FastAPI target unreachable from web host.

Fix:
- verify FastAPI process and bind address.
- check host firewall and route.

## 8.3 Temporal shows no activities / "No worker running"
Cause:
- worker process not running or dependency missing.

Fix:
- restart worker on instance.
- inspect `/var/log/worker.log`.
- resolve runtime dependency errors (for example `faster_whisper`).

## 8.4 Workflow completed, MinIO has objects, homepage unchanged
Cause:
- index refresh path mismatch or web host index authority mismatch.

Fix:
- validate `REINDEX_URL` reachability from worker host.
- ensure index generation writes the web host authoritative data source.

---

## 9. Operational Rules

1. Keep control plane and web ownership explicit (`huihuang`).
2. Keep GPU-heavy activities on instance.
3. Avoid mixed tunnel + direct path assumptions in normal operation.
4. Any endpoint migration must be followed by:
   - env update,
   - service restart,
   - `/health` verification,
   - one smoke query.
5. Image release policy:
   - publish `:canary` first,
   - promote to `:stable` only after runtime validation.
6. Worker startup policy:
   - `worker-cpu` and `worker-gpu` are on-demand (not autostart),
   - scheduler-trigger endpoints can request worker start via supervisor.

## 9.1 Release/Validation Pipeline

- GHCR workflow: `.github/workflows/deploy.yml`
  - default publish tag: `canary`
  - optional stable promotion input: `promote_stable=true`
- Minimal boot CI: `.github/workflows/ci-minimal-image.yml`
  - validates build + container boot + dependency wiring + queue registration smoke.

---

## 10. Rollback Strategy

If hybrid mode is unstable:

1. Preserve current config snapshot (`.env`, startup scripts, host service tasks).
2. Switch to known-good fallback profile (all services on instance or previous external profile).
3. Restart in dependency order:
   - control plane,
   - object store,
   - API,
   - worker,
   - web.
4. Run smoke verification:
   - query 1 keyword, 2-3 results,
   - confirm Temporal completion,
   - confirm MinIO artifacts,
   - confirm homepage visibility.

---

## 11. Notes

- `docs/tailscale_control_plane.md` documents an older phase and should be treated as historical reference unless explicitly re-enabled.
- This summary is the current operational baseline for hybrid deployment.
