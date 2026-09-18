#!/usr/bin/env bash
# Starts the MeetSage backend and frontend as background processes.
# Safe to re-run: it refuses to start a component that already has a running PID.
#
# Modes (MEETSAGE_MODE env var):
#   dev (default) - backend on $MEETSAGE_BACKEND_PORT + a separate Vite dev
#                    server on $MEETSAGE_FRONTEND_PORT, with hot reload.
#   production     - starts only the backend, which serves the already-built
#                    frontend/dist itself on the same origin (no CORS, one
#                    process). Build it first: ./scripts/build_frontend.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUN_DIR="$ROOT_DIR/data/run"
LOG_DIR="$ROOT_DIR/data/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

BACKEND_HOST="${MEETSAGE_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${MEETSAGE_BACKEND_PORT:-8000}"
FRONTEND_PORT="${MEETSAGE_FRONTEND_PORT:-5173}"
MODE="${MEETSAGE_MODE:-dev}"

if [ "$MODE" = "production" ] && [ ! -d "$FRONTEND_DIR/dist" ]; then
    echo "MEETSAGE_MODE=production but frontend/dist doesn't exist yet." >&2
    echo "Run ./scripts/build_frontend.sh first." >&2
    exit 1
fi

is_running() {
    local pid_file="$1"
    [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

if is_running "$RUN_DIR/backend.pid"; then
    echo "Backend already running (PID $(cat "$RUN_DIR/backend.pid"))."
else
    echo "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT ..."
    (
        cd "$BACKEND_DIR"
        # shellcheck disable=SC1091
        source venv/bin/activate
        # setsid makes this process its own session/process-group leader (PID==PGID),
        # so stop.sh can reliably kill the whole group later.
        setsid nohup python -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
            > "$LOG_DIR/backend.log" 2>&1 &
        echo $! > "$RUN_DIR/backend.pid"
    )
    sleep 2
    if is_running "$RUN_DIR/backend.pid"; then
        echo "Backend started (PID $(cat "$RUN_DIR/backend.pid")). Logs: data/logs/backend.log"
    else
        echo "Backend failed to start — check data/logs/backend.log" >&2
        exit 1
    fi
fi

if [ "$MODE" = "production" ]; then
    cat <<EOF

MeetSage is running (production mode — one process):
  UI/API:  http://$BACKEND_HOST:$BACKEND_PORT
  Docs:    http://$BACKEND_HOST:$BACKEND_PORT/docs

Stop with:  ./scripts/stop.sh
Check with: ./scripts/health_check.sh
EOF
    exit 0
fi

if is_running "$RUN_DIR/frontend.pid"; then
    echo "Frontend already running (PID $(cat "$RUN_DIR/frontend.pid"))."
else
    echo "Starting frontend on http://localhost:$FRONTEND_PORT ..."
    (
        cd "$FRONTEND_DIR"
        # setsid so the whole npm -> vite process tree shares one killable process group.
        setsid nohup npm run dev -- --port "$FRONTEND_PORT" --host \
            > "$LOG_DIR/frontend.log" 2>&1 &
        echo $! > "$RUN_DIR/frontend.pid"
    )
    sleep 2
    if is_running "$RUN_DIR/frontend.pid"; then
        echo "Frontend started (PID $(cat "$RUN_DIR/frontend.pid")). Logs: data/logs/frontend.log"
    else
        echo "Frontend failed to start — check data/logs/frontend.log" >&2
        exit 1
    fi
fi

cat <<EOF

MeetSage is running (dev mode):
  UI:      http://localhost:$FRONTEND_PORT
  API:     http://$BACKEND_HOST:$BACKEND_PORT
  Docs:    http://$BACKEND_HOST:$BACKEND_PORT/docs

Stop with:  ./scripts/stop.sh
Check with: ./scripts/health_check.sh
EOF
