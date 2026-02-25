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
python3 - <<'PY'
from pathlib import Path
import shutil

src_root = Path('/srv/ledge-repo')
dst_root = Path('/srv/project/cres_ytdlp/compute/ledge')

if dst_root.exists():
    shutil.rmtree(dst_root)

files = [
    'requirements.instance.txt',
    'configs/temporal.yaml',
    'configs/minio.yaml',
    'configs/models.yaml',
    'src/backend/__init__.py',
    'src/backend/worker.py',
    'src/backend/worker_cpu.py',
    'src/backend/activities/__init__.py',
    'src/backend/activities/stt_activity.py',
    'src/backend/activities/tts_activity.py',
    'src/backend/activities/llm_activity.py',
    'src/backend/workflows/__init__.py',
    'src/backend/workflows/voice_workflow.py',
    'src/backend/workflows/transcribe_workflow.py',
    'src/shared/__init__.py',
    'src/shared/config.py',
    'src/shared/constants.py',
    'src/shared/logger.py',
    'src/shared/models.py',
    'src/api/compute/__init__.py',
    'src/api/compute/main.py',
    'src/api/compute/routes/__init__.py',
    'src/api/compute/routes/health.py',
    'src/api/compute/routes/stt.py',
    'src/api/compute/routes/tts.py',
]

for rel in files:
    s = src_root / rel
    d = dst_root / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)

(dst_root / 'src' / '__init__.py').write_text('"""Ledge compute bundle package root."""\n', encoding='utf-8')
PY
```

Rules:
- Do not place secrets in this directory.
- Keep changes minimal and limited to compute runtime requirements.
