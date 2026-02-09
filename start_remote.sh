#!/bin/bash
# Unified Service Startup Script
set -e

cd /workspace
PID_DIR="/workspace/run"
mkdir -p "$PID_DIR"

# Normalize line endings to avoid Windows CRLF startup issues.
sed -i 's/\r$//' /workspace/start_remote.sh /workspace/entrypoint.sh /workspace/deploy_vast.sh /workspace/onstart.sh 2>/dev/null || true

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

show_status() {
    echo "== CRES Service Status =="
    pid_status_line "next-wrapper" "$PID_DIR/cres_next_wrapper.pid"
    pid_status_line "worker" "$PID_DIR/cres_worker.pid"
    pid_status_line "fastapi" "$PID_DIR/cres_fastapi.pid"
    pid_status_line "llama" "$PID_DIR/cres_llama.pid"
    pid_status_line "temporal" "$PID_DIR/cres_temporal.pid"
    pid_status_line "minio" "$PID_DIR/cres_minio.pid"
    echo
    check_http "Next.js" "http://127.0.0.1:3000"
    check_http "FastAPI" "http://127.0.0.1:8000/health"
    check_http "MinIO" "http://127.0.0.1:9000/minio/health/live"
    check_http "Temporal UI" "http://127.0.0.1:8233"
    echo
    echo "== Recent Logs =="
    echo "-- /workspace/logs/app.log --"
    tail -n 20 /workspace/logs/app.log 2>/dev/null || true
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
        if [ "$cwd" = "/workspace/web" ]; then
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
        if [ "$cwd" = "/workspace/web" ]; then
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
        if [ "$cwd" = "/workspace/web" ]; then
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
    pkill -9 -f "/workspace/entrypoint.sh bash -c cd /workspace/web && npm start" || true
    pkill -9 -f "uvicorn src.api.main:app --host 0.0.0.0 --port 8000" || true
    pkill -9 -f "python3 -m src.backend.worker" || true
    pkill -9 -f "temporal server start-dev --ip 0.0.0.0" || true
    pkill -9 -f "minio server ./data/minio --address :9000 --console-address :9001" || true
    sleep 2

    # Environment setup.
    export LLM_MODEL_PATH="${LLM_MODEL_PATH:-/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
    export WHISPER_MODEL_PATH="${WHISPER_MODEL_PATH:-/workspace/packages/models/whisper}"
    export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin:/workspace:${PATH}"
    mkdir -p /workspace/logs

    echo "Starting services via entrypoint..."
    rm -f "$PID_DIR/cres_next_wrapper.pid"
    if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://127.0.0.1:3000 || true)" = "200" ]; then
        echo "Detected healthy service on :3000, skipping Next.js relaunch command."
        nohup /workspace/entrypoint.sh bash -lc "while true; do sleep 3600; done" > /workspace/logs/app.log 2>&1 &
        echo $! > "$PID_DIR/cres_next_wrapper.pid"
    else
        nohup /workspace/entrypoint.sh bash -c "cd /workspace/web && npm start" > /workspace/logs/app.log 2>&1 &
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
