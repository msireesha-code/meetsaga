#!/usr/bin/env bash
# Builds the frontend for production-style same-origin serving by the backend
# (see backend/app/main.py — it serves frontend/dist itself when present, no
# separate Vite dev server or CORS needed). Re-run this after any frontend
# change you want reflected outside the Vite dev server.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Frontend dependencies not installed — run ./scripts/install.sh first." >&2
    exit 1
fi

echo "Building frontend..."
(cd "$FRONTEND_DIR" && npm run build)

echo "Built to frontend/dist/ — the backend will serve it automatically on its own port."
echo "Restart the backend if it was already running: ./scripts/stop.sh && ./scripts/start.sh"
