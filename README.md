# cres_ytdlp

`cres_ytdlp` is the channel repository for building and publishing the GPU runtime image.

## 发布流程（本地先同步，再触发 GHCR）

- `cres_ytdlp` is the only GHCR build/publish channel.
- GitHub Actions no longer checks out `jianshelu/ledge-repo` during app-image build.
- Before each release from iris, sync local source into `compute/ledge/` first:

```bash
/srv/project/cres_ytdlp/scripts/sync_ledge_allowlist.sh \
  /srv/ledge-repo \
  /srv/project/cres_ytdlp/compute/ledge
```

- Synced allowlist (into `compute/ledge/`):
  - `src/backend/`
  - `src/shared/`
  - `src/api/compute/`
  - `configs/models.yaml`
  - `configs/minio.yaml`
  - `configs/temporal.yaml`
  - `requirements.instance.txt`
- After sync, commit and push in `cres_ytdlp`; the push triggers GHCR workflow.
- `ledge-repo` does not need to be pushed remotely for release, as long as local sync is completed before pushing `cres_ytdlp`.

## GPU 镜像仅含 compute runtime

- Default image scope is GPU runtime only (`llama.cpp`, compute FastAPI, workers, supervisord/runtime scripts).
- Control-plane and web are excluded from the default GPU image boundary.
- Control-plane code remains on the control host and is synced separately only when explicitly required.
