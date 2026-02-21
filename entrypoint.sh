#!/usr/bin/env bash
set -euo pipefail

cd /workspace

mkdir -p /workspace/logs /workspace/run /workspace/scripts

PROJECT_PROFILE="${PROJECT_PROFILE:-cres}"

project_has_layout() {
  local root="$1"
  local profile="$2"

  if [ ! -d "$root" ]; then
    return 1
  fi

  case "$profile" in
    cres)
      [ -f "$root/src/api/main.py" ] && [ -f "$root/src/backend/worker.py" ]
      ;;
    ledge)
      [ -f "$root/src/api/compute/main.py" ] \
        && [ -f "$root/src/backend/worker.py" ] \
        && [ -f "$root/src/backend/worker_cpu.py" ] \
        && [ -d "$root/src/shared" ]
      ;;
    *)
      return 1
      ;;
  esac
}

clone_ledge_repo() {
  local target_root="$1"
  local repo_url="${LEDGE_REPO_URL:-}"
  local repo_ref="${LEDGE_REPO_REF:-main}"
  local ssh_cmd=""
  local clone_url=""
  local repo_display=""
  local askpass_file=""
  local use_https_token="0"

  cleanup_askpass() {
    if [ -n "$askpass_file" ] && [ -f "$askpass_file" ]; then
      rm -f "$askpass_file"
    fi
  }

  run_git() {
    if [ -n "$ssh_cmd" ]; then
      GIT_SSH_COMMAND="$ssh_cmd" "$@"
      return
    fi

    if [ "$use_https_token" = "1" ]; then
      askpass_file="$(mktemp /tmp/ledge-askpass.XXXXXX)"
      chmod 700 "$askpass_file"
      cat > "$askpass_file" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  *Username*) printf '%s\n' "${LEDGE_GITHUB_USER:-x-access-token}" ;;
  *Password*) printf '%s\n' "${LEDGE_GITHUB_TOKEN:-}" ;;
  *) printf '\n' ;;
esac
EOF
      if ! GIT_TERMINAL_PROMPT=0 GIT_ASKPASS="$askpass_file" "$@"; then
        local rc=$?
        cleanup_askpass
        return $rc
      fi
      cleanup_askpass
      return 0
    fi

    "$@"
  }

  if [ -n "${LEDGE_GIT_SSH_COMMAND:-}" ]; then
    ssh_cmd="${LEDGE_GIT_SSH_COMMAND}"
  elif [ -n "${LEDGE_GIT_SSH_KEY_PATH:-}" ]; then
    ssh_cmd="ssh -i ${LEDGE_GIT_SSH_KEY_PATH} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
  fi

  if [ -z "$repo_url" ] && [ -n "${LEDGE_GITHUB_TOKEN:-}" ]; then
    repo_url="https://github.com/jianshelu/ledge-repo.git"
  fi
  if [ -z "$repo_url" ]; then
    return 1
  fi

  clone_url="$repo_url"
  if [ -n "${LEDGE_GITHUB_TOKEN:-}" ] && [[ "$repo_url" == https://github.com/* ]]; then
    use_https_token="1"
  fi
  repo_display="$repo_url"

  if ! command -v git >/dev/null 2>&1; then
    echo "[entrypoint] git is required for LEDGE_REPO_URL bootstrap" >&2
    return 1
  fi

  mkdir -p "$(dirname "$target_root")"
  if [ -d "$target_root/.git" ]; then
    echo "[entrypoint] updating existing ledge repo at ${target_root} (${repo_ref})"
    run_git git -C "$target_root" fetch --depth 1 origin "$repo_ref"
    run_git git -C "$target_root" checkout -f FETCH_HEAD
  else
    if [ -d "$target_root" ] && [ -n "$(ls -A "$target_root" 2>/dev/null || true)" ]; then
      echo "[entrypoint] ${target_root} exists and is not a git repo; refusing to overwrite" >&2
      return 1
    fi
    echo "[entrypoint] cloning ledge repo ${repo_display} (${repo_ref}) into ${target_root}"
    rm -rf "$target_root"
    run_git git clone --depth 1 --branch "$repo_ref" "$clone_url" "$target_root"
  fi

  cleanup_askpass
}

case "${PROJECT_PROFILE}" in
  cres)
    default_project_root="/workspace"
    default_supervisord_config="/etc/supervisor/supervisord.cres.conf"
    default_api_role="compute"
    ;;
  ledge)
    default_project_root="/workspace/ledge-repo"
    default_supervisord_config="/etc/supervisor/supervisord.ledge.conf"
    default_api_role="compute"
    ;;
  *)
    echo "[entrypoint] unsupported PROJECT_PROFILE=${PROJECT_PROFILE} (expected: cres|ledge)" >&2
    exit 1
    ;;
esac

export PROJECT_ROOT="${PROJECT_ROOT:-${default_project_root}}"
SUPERVISORD_CONFIG="${SUPERVISORD_CONFIG:-${default_supervisord_config}}"

if [ "${PROJECT_PROFILE}" = "ledge" ]; then
  if project_has_layout "${PROJECT_ROOT}" "ledge"; then
    :
  elif [ "${PROJECT_ROOT}" != "${default_project_root}" ] && project_has_layout "${default_project_root}" "ledge"; then
    echo "[entrypoint] PROJECT_ROOT=${PROJECT_ROOT} is not a ledge source tree, using ${default_project_root}" >&2
    export PROJECT_ROOT="${default_project_root}"
  else
    clone_ledge_repo "${default_project_root}" || true
    if project_has_layout "${default_project_root}" "ledge"; then
      export PROJECT_ROOT="${default_project_root}"
    else
      echo "[entrypoint] ledge profile requires a ledge source tree" >&2
      echo "[entrypoint] missing required files under PROJECT_ROOT=${PROJECT_ROOT}" >&2
      echo "[entrypoint] options:" >&2
      echo "[entrypoint]   1) mount ledge repo at ${default_project_root}" >&2
      echo "[entrypoint]   2) set LEDGE_REPO_URL (+ optional LEDGE_REPO_REF, LEDGE_GIT_SSH_KEY_PATH) for auto-clone" >&2
      echo "[entrypoint]   3) set LEDGE_GITHUB_TOKEN (and optional LEDGE_GITHUB_USER) for HTTPS auto-clone" >&2
      exit 1
    fi
  fi
else
  if ! project_has_layout "${PROJECT_ROOT}" "cres"; then
    echo "[entrypoint] invalid PROJECT_ROOT for cres profile: ${PROJECT_ROOT}" >&2
    echo "[entrypoint] expected files: src/api/main.py and src/backend/worker.py" >&2
    exit 1
  fi
fi

# Safe defaults for compute-node style runtime.
export PYTHONPATH="${PYTHONPATH:-${PROJECT_ROOT}}"
export API_ROLE="${API_ROLE:-${default_api_role}}"
export AUTO_REINDEX_ON_START="${AUTO_REINDEX_ON_START:-false}"
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-64.229.113.233:7233}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-64.229.113.233:9000}"
export MINIO_SECURE="${MINIO_SECURE:-false}"

# CI/no-GPU hosts can opt out cleanly; runtime can override.
export WORKER_GPU_OPTIONAL="${WORKER_GPU_OPTIONAL:-1}"
export LLAMA_DISABLE="${LLAMA_DISABLE:-0}"

SUPERVISORD_BIN="$(command -v supervisord || true)"
if [ -z "${SUPERVISORD_BIN}" ]; then
  echo "[entrypoint] supervisord not found in PATH" >&2
  exit 1
fi

if [ ! -f "${SUPERVISORD_CONFIG}" ]; then
  echo "[entrypoint] missing ${SUPERVISORD_CONFIG}" >&2
  exit 1
fi

ln -sf "${SUPERVISORD_CONFIG}" /etc/supervisor/supervisord.conf

echo "[entrypoint] profile=${PROJECT_PROFILE} project_root=${PROJECT_ROOT} supervisor=${SUPERVISORD_CONFIG}"

exec "${SUPERVISORD_BIN}" -n -c "${SUPERVISORD_CONFIG}"
