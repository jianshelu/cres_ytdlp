#!/bin/bash
# Unified Service Startup Script
set -e

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
if [ ! -w "$WORKSPACE_ROOT" ]; then
    WORKSPACE_ROOT="$(pwd)"
fi

cd "$WORKSPACE_ROOT"
PID_DIR="$WORKSPACE_ROOT/run"
mkdir -p "$PID_DIR"

# Load runtime env from .env when present so restart/status use the same endpoints/credentials.
load_workspace_env() {
    local env_file="$WORKSPACE_ROOT/.env"
    if [ -f "$env_file" ]; then
        set -a
        # shellcheck disable=SC1090
        . "$env_file"
        set +a
    fi
}

load_workspace_env

# Normalize line endings to avoid Windows CRLF startup issues.
sed -i 's/\r$//' "$WORKSPACE_ROOT/start_remote.sh" "$WORKSPACE_ROOT/entrypoint.sh" "$WORKSPACE_ROOT/onstart.sh" 2>/dev/null || true

SUPERVISOR_SOCKET="${SUPERVISOR_SOCKET:-unix:///tmp/supervisor.sock}"
SUPERVISOR_SOCKET_PATH="${SUPERVISOR_SOCKET#unix://}"

supervisor_status_raw() {
    supervisorctl -s "$SUPERVISOR_SOCKET" status 2>/dev/null
}

detect_supervisor_conf() {
    if [ -n "${SUPERVISOR_CONF:-}" ] && [ -f "${SUPERVISOR_CONF}" ]; then
        echo "${SUPERVISOR_CONF}"
        return 0
    fi
    for candidate in "/etc/supervisor/supervisord.conf" "$WORKSPACE_ROOT/scripts/supervisord.conf"; do
        if [ -f "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

supervisor_controls_backend() {
    if ! command -v supervisorctl >/dev/null 2>&1; then
        return 1
    fi
    if [[ "$SUPERVISOR_SOCKET" == unix://* ]] && [ ! -S "$SUPERVISOR_SOCKET_PATH" ]; then
        return 1
    fi
    local status
    if ! status="$(supervisor_status_raw)"; then
        return 1
    fi
    if [ -z "$status" ]; then
        return 1
    fi
    # Require at least one valid supervisord program status line.
    # This avoids treating supervisorctl transport errors as a healthy backend.
    if ! echo "$status" | grep -Eq '^[[:alnum:]_.-]+[[:space:]]+(RUNNING|STARTING|BACKOFF|STOPPED|FATAL|EXITED|UNKNOWN)[[:space:]]'; then
        return 1
    fi
    return 0
}

ensure_supervisor_backend() {
    if supervisor_controls_backend; then
        return 0
    fi
    if ! command -v supervisord >/dev/null 2>&1; then
        return 1
    fi
    local conf
    conf="$(detect_supervisor_conf 2>/dev/null || true)"
    if [ -z "$conf" ]; then
        return 1
    fi

    echo "Supervisor backend not detected. Starting supervisord with: $conf"
    nohup "$(command -v supervisord)" -n -c "$conf" >/var/log/supervisord-bootstrap.log 2>&1 &

    for _ in $(seq 1 20); do
        if supervisor_controls_backend; then
            return 0
        fi
        sleep 1
    done
    return 1
}

pid_status_line() {
    local name="$1"
    local pid_file="$2"
    if [ ! -f "$pid_file" ]; then
        echo "[MISSING] $name pid file not found"
        return
    fi
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [ -z "$pid" ]; then
        echo "[EMPTY]   $name pid file exists but empty"
        return
    fi
    if kill -0 "$pid" 2>/dev/null; then
        echo "[RUNNING] $name pid=$pid"
    else
        echo "[STALE]   $name pid=$pid not alive"
    fi
}

check_http() {
    local name="$1"
    local url="$2"
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "$url" || true)"
    if [ "$code" = "200" ]; then
        echo "[OK]      $name $url"
    else
        echo "[FAIL]    $name $url code=$code"
    fi
}

check_temporal_grpc() {
    local target="$1"
    if ! python3 -c "import temporalio" >/dev/null 2>&1; then
        local host="${target%:*}"
        local port="${target##*:}"
        if command -v nc >/dev/null 2>&1; then
            if nc -z -w 3 "$host" "$port" >/dev/null 2>&1; then
                echo "[OK]      Temporal TCP ${target} (temporalio missing locally)"
            else
                echo "[FAIL]    Temporal TCP ${target} (temporalio missing locally)"
            fi
        else
            echo "[WARN]    temporalio and nc both unavailable; skip Temporal check for ${target}"
        fi
        return
    fi
    python3 - "$target" <<'PY'
import asyncio
import sys
from temporalio.client import Client

target = sys.argv[1]

async def main():
    try:
        await Client.connect(target)
        print(f"[OK]      Temporal gRPC {target}")
    except Exception as e:
        print(f"[FAIL]    Temporal gRPC {target} err={e}")

asyncio.run(main())
PY
}

show_status() {
    local control_plane_mode="${CONTROL_PLANE_MODE:-external}"
    local temporal_addr="${TEMPORAL_ADDRESS:-localhost:7233}"
    local minio_endpoint="${MINIO_ENDPOINT:-localhost:9000}"
    local minio_scheme="http"
    if [ "${MINIO_SECURE:-false}" = "true" ] || [ "${MINIO_SECURE:-false}" = "1" ]; then
        minio_scheme="https"
    fi
    echo "== CRES Service Status =="
    pid_status_line "next-wrapper" "$PID_DIR/cres_next_wrapper.pid"
    pid_status_line "worker" "$PID_DIR/cres_worker.pid"
    pid_status_line "fastapi" "$PID_DIR/cres_fastapi.pid"
    pid_status_line "llama" "$PID_DIR/cres_llama.pid"
    if [ "$control_plane_mode" = "local" ]; then
        pid_status_line "temporal" "$PID_DIR/cres_temporal.pid"
        pid_status_line "minio" "$PID_DIR/cres_minio.pid"
    fi
    echo
    check_http "Next.js" "http://127.0.0.1:3000"
    check_http "FastAPI" "http://127.0.0.1:8000/health"
    check_http "MinIO" "${minio_scheme}://${minio_endpoint}/minio/health/live"
    check_temporal_grpc "${temporal_addr}"
    if supervisor_controls_backend; then
        echo
        echo "== Supervisor Programs =="
        supervisor_status_raw
    fi
    echo
    echo "== Recent Logs =="
    echo "-- $WORKSPACE_ROOT/logs/app.log --"
    tail -n 20 "$WORKSPACE_ROOT/logs/app.log" 2>/dev/null || true
    echo "-- /var/log/fastapi.log --"
    tail -n 20 /var/log/fastapi.log 2>/dev/null || true
    echo "-- /var/log/worker.log --"
    tail -n 20 /var/log/worker.log 2>/dev/null || true
    echo "-- /var/log/worker-cpu.log --"
    tail -n 20 /var/log/worker-cpu.log 2>/dev/null || true
    echo "-- /var/log/worker-gpu.log --"
    tail -n 20 /var/log/worker-gpu.log 2>/dev/null || true
}

terminate_pidfile() {
    local pid_file="$1"
    if [ ! -f "$pid_file" ]; then
        return 0
    fi
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [ -z "$pid" ]; then
        rm -f "$pid_file"
        return 0
    fi
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        sleep 1
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
}

terminate_workspace_next() {
    local pids
    pids="$(pgrep -f "next start" || true)"
    if [ -z "$pids" ]; then
        return 0
    fi
    for pid in $pids; do
        local cwd
        cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
        if [ "$cwd" = "$WORKSPACE_ROOT/web" ]; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
}

has_workspace_next_server() {
    local pids
    pids="$(pgrep -x next-server || true)"
    if [ -z "$pids" ]; then
        return 1
    fi
    for pid in $pids; do
        local cwd
        cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
        if [ "$cwd" = "$WORKSPACE_ROOT/web" ]; then
            return 0
        fi
    done
    return 1
}

terminate_workspace_next_server() {
    local pids
    pids="$(pgrep -x next-server || true)"
    if [ -z "$pids" ]; then
        return 0
    fi
    for pid in $pids; do
        local cwd
        cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
        if [ "$cwd" = "$WORKSPACE_ROOT/web" ]; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
}

restart_services() {
    local supervisor_backend=0
    if ensure_supervisor_backend; then
        supervisor_backend=1
    fi

    echo "Cleaning up existing project processes..."
    # Kill only PIDs previously created by this project.
    terminate_pidfile "$PID_DIR/cres_next_wrapper.pid"
    if [ "$supervisor_backend" -eq 0 ]; then
        terminate_pidfile "$PID_DIR/cres_worker.pid"
        terminate_pidfile "$PID_DIR/cres_fastapi.pid"
        terminate_pidfile "$PID_DIR/cres_llama.pid"
    else
        rm -f "$PID_DIR/cres_worker.pid" "$PID_DIR/cres_fastapi.pid" "$PID_DIR/cres_llama.pid"
    fi
    terminate_pidfile "$PID_DIR/cres_temporal.pid"
    terminate_pidfile "$PID_DIR/cres_minio.pid"
    terminate_workspace_next
    terminate_workspace_next_server

    # Conservative fallback for stale processes from old scripts.
    pkill -9 -f "$WORKSPACE_ROOT/entrypoint.sh bash -c cd $WORKSPACE_ROOT/web && npm start" || true
    if [ "$supervisor_backend" -eq 0 ]; then
        pkill -9 -f "uvicorn src.api.main:app --host 0.0.0.0 --port 8000" || true
        pkill -9 -f "python3 -m src.backend.worker" || true
    fi
    sleep 2

    # Environment setup.
    export LLM_MODEL_PATH="${LLM_MODEL_PATH:-$WORKSPACE_ROOT/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
    export WHISPER_MODEL_PATH="${WHISPER_MODEL_PATH:-$WORKSPACE_ROOT/packages/models/whisperx}"
    export BASE_TASK_QUEUE="${BASE_TASK_QUEUE:-video-processing}"
    export SCHEDULER_ACTIVE_INSTANCE="${SCHEDULER_ACTIVE_INSTANCE:-true}"
    export SCHEDULER_ACTIVE_MAX_PARALLELISM="${SCHEDULER_ACTIVE_MAX_PARALLELISM:-2}"
    export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-64.229.113.233:7233}"
    export MINIO_ENDPOINT="${MINIO_ENDPOINT:-64.229.113.233:9000}"
    export MINIO_SECURE="${MINIO_SECURE:-false}"
    export REINDEX_URL="${REINDEX_URL:-http://64.229.113.233:8000/admin/reindex}"
    export CONTROL_PLANE_MODE="${CONTROL_PLANE_MODE:-external}"
    export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin:$WORKSPACE_ROOT:${PATH}"
    mkdir -p "$WORKSPACE_ROOT/logs"

    if [ -f "$WORKSPACE_ROOT/scripts/setup_tailscale.sh" ]; then
        chmod +x "$WORKSPACE_ROOT/scripts/setup_tailscale.sh"
        "$WORKSPACE_ROOT/scripts/setup_tailscale.sh" || true
    fi

    rm -f "$PID_DIR/cres_next_wrapper.pid"
    if [ "$supervisor_backend" -eq 1 ]; then
        echo "Supervisor is managing backend services; restarting Next.js only."
        if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://127.0.0.1:3000 || true)" = "200" ]; then
            echo "Detected healthy service on :3000, skipping Next.js relaunch command."
            nohup bash -lc "while true; do sleep 3600; done" > "$WORKSPACE_ROOT/logs/app.log" 2>&1 &
            echo $! > "$PID_DIR/cres_next_wrapper.pid"
        else
            nohup bash -lc "cd '$WORKSPACE_ROOT/web' && npm start" > "$WORKSPACE_ROOT/logs/app.log" 2>&1 &
            echo $! > "$PID_DIR/cres_next_wrapper.pid"
        fi
    else
        echo "Supervisor backend unavailable. Falling back to entrypoint startup path."
        if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://127.0.0.1:3000 || true)" = "200" ]; then
            echo "Detected healthy service on :3000, skipping Next.js relaunch command."
            nohup "$WORKSPACE_ROOT/entrypoint.sh" bash -lc "while true; do sleep 3600; done" > "$WORKSPACE_ROOT/logs/app.log" 2>&1 &
            echo $! > "$PID_DIR/cres_next_wrapper.pid"
        else
            nohup "$WORKSPACE_ROOT/entrypoint.sh" bash -c "cd $WORKSPACE_ROOT/web && npm start" > "$WORKSPACE_ROOT/logs/app.log" 2>&1 &
            echo $! > "$PID_DIR/cres_next_wrapper.pid"
        fi
    fi
    echo "Started. Monitor status with: ./start_remote.sh --status"
}

case "${1:-}" in
    --status)
        show_status
        ;;
    --restart|"")
        restart_services
        ;;
    *)
        echo "Usage: ./start_remote.sh [--restart|--status]"
        exit 1
        ;;
esac

