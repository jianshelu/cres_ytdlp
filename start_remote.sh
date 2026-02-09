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

# Normalize line endings to avoid Windows CRLF startup issues.
sed -i 's/\r$//' "$WORKSPACE_ROOT/start_remote.sh" "$WORKSPACE_ROOT/entrypoint.sh" "$WORKSPACE_ROOT/deploy_vast.sh" "$WORKSPACE_ROOT/onstart.sh" 2>/dev/null || true

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
    echo
    echo "== Recent Logs =="
    echo "-- $WORKSPACE_ROOT/logs/app.log --"
    tail -n 20 "$WORKSPACE_ROOT/logs/app.log" 2>/dev/null || true
    echo "-- /var/log/fastapi.log --"
    tail -n 20 /var/log/fastapi.log 2>/dev/null || true
    echo "-- /var/log/worker.log --"
    tail -n 20 /var/log/worker.log 2>/dev/null || true
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
    echo "Cleaning up existing project processes..."
    # Kill only PIDs previously created by this project.
    terminate_pidfile "$PID_DIR/cres_next_wrapper.pid"
    terminate_pidfile "$PID_DIR/cres_worker.pid"
    terminate_pidfile "$PID_DIR/cres_fastapi.pid"
    terminate_pidfile "$PID_DIR/cres_llama.pid"
    terminate_pidfile "$PID_DIR/cres_temporal.pid"
    terminate_pidfile "$PID_DIR/cres_minio.pid"
    terminate_workspace_next
    terminate_workspace_next_server

    # Conservative fallback for stale processes from old scripts.
    pkill -9 -f "$WORKSPACE_ROOT/entrypoint.sh bash -c cd $WORKSPACE_ROOT/web && npm start" || true
    pkill -9 -f "uvicorn src.api.main:app --host 0.0.0.0 --port 8000" || true
    pkill -9 -f "python3 -m src.backend.worker" || true
    sleep 2

    # Environment setup.
    export LLM_MODEL_PATH="${LLM_MODEL_PATH:-$WORKSPACE_ROOT/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
    export WHISPER_MODEL_PATH="${WHISPER_MODEL_PATH:-$WORKSPACE_ROOT/packages/models/whisper}"
    export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-100.121.250.72:7233}"
    export MINIO_ENDPOINT="${MINIO_ENDPOINT:-100.121.250.72:9000}"
    export MINIO_SECURE="${MINIO_SECURE:-false}"
    export CONTROL_PLANE_MODE="${CONTROL_PLANE_MODE:-external}"
    export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin:$WORKSPACE_ROOT:${PATH}"
    mkdir -p "$WORKSPACE_ROOT/logs"

    if [ -f "$WORKSPACE_ROOT/scripts/setup_tailscale.sh" ]; then
        chmod +x "$WORKSPACE_ROOT/scripts/setup_tailscale.sh"
        "$WORKSPACE_ROOT/scripts/setup_tailscale.sh" || true
    fi

    echo "Starting services via entrypoint..."
    rm -f "$PID_DIR/cres_next_wrapper.pid"
    if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://127.0.0.1:3000 || true)" = "200" ]; then
        echo "Detected healthy service on :3000, skipping Next.js relaunch command."
        nohup "$WORKSPACE_ROOT/entrypoint.sh" bash -lc "while true; do sleep 3600; done" > "$WORKSPACE_ROOT/logs/app.log" 2>&1 &
        echo $! > "$PID_DIR/cres_next_wrapper.pid"
    else
        nohup "$WORKSPACE_ROOT/entrypoint.sh" bash -c "cd $WORKSPACE_ROOT/web && npm start" > "$WORKSPACE_ROOT/logs/app.log" 2>&1 &
        echo $! > "$PID_DIR/cres_next_wrapper.pid"
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
