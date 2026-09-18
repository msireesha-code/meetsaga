#!/usr/bin/env bash
# Stops MeetSage backend and frontend processes started by scripts/start.sh.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/data/run"

stop_one() {
    local name="$1"
    local pid_file="$RUN_DIR/$name.pid"
    if [ ! -f "$pid_file" ]; then
        echo "$name: not running (no PID file)."
        return
    fi
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
        # start.sh launches with setsid, so PID == process group ID; killing the
        # negative PID kills the whole tree (e.g. npm's spawned vite child), not
        # just the top-level wrapper process.
        kill -TERM -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null
        for _ in $(seq 1 10); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.5
        done
        if kill -0 "$pid" 2>/dev/null; then
            echo "$name: did not stop gracefully, sending SIGKILL to process group $pid."
            kill -KILL -- "-$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
        else
            echo "$name: stopped (PID $pid)."
        fi
    else
        echo "$name: PID file present but process $pid not running (stale)."
    fi
    rm -f "$pid_file"
}

stop_one backend
stop_one frontend
