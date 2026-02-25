# Compute Bundle

This directory vendors runtime-only compute code that is required when the
`cres_ytdlp` GHCR image runs with `PROJECT_PROFILE=ledge`.

Why this exists:
- Image build and publish happen in the `cres_ytdlp` repository.
- GPU instances may need to execute Ledge compute runtime without cloning at boot.

Current bundle location:
- `compute/ledge/`

Contents (GPU runtime required services only):
- `compute/ledge/src/backend/worker.py`
- `compute/ledge/src/backend/worker_cpu.py`
- `compute/ledge/src/backend/activities/{stt_activity.py,tts_activity.py,llm_activity.py}`
- `compute/ledge/src/backend/workflows/{voice_workflow.py,transcribe_workflow.py}`
- `compute/ledge/src/shared/{config.py,constants.py,logger.py,models.py}`
- `compute/ledge/src/api/compute/**`
- `compute/ledge/configs/{temporal.yaml,minio.yaml,models.yaml}`
- `compute/ledge/requirements.instance.txt` (reference only)

Not bundled into image:
- `src/api/control/**` and other non-GPU control-plane code
- These are synchronized from control host to instance over SSH only when needed.

Refresh bundle from local `ledge-repo` workspace:

```bash
/srv/project/cres_ytdlp/scripts/sync_ledge_allowlist.sh \
  /srv/ledge-repo \
  /srv/project/cres_ytdlp/compute/ledge
```

Rules:
- Do not place secrets in this directory.
- Keep changes minimal and limited to compute runtime requirements.
