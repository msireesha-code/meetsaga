#!/usr/bin/env bash
# Verifies MeetSage's runtime health: backend, database, storage, FFmpeg,
# FFprobe, configuration, installed models, disk space.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

BACKEND_HOST="${MEETSAGE_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${MEETSAGE_BACKEND_PORT:-8000}"
BASE_URL="http://$BACKEND_HOST:$BACKEND_PORT"

FAILURES=0
WARNINGS=0

pass() { echo "[PASS] $1"; }
warn() { echo "[WARN] $1"; WARNINGS=$((WARNINGS+1)); }
fail() { echo "[FAIL] $1"; FAILURES=$((FAILURES+1)); }

echo "== MeetSage Health Check =="

# Backend
if curl -fsS "$BASE_URL/api/system/health" >/dev/null 2>&1; then
    pass "Backend is reachable at $BASE_URL"
else
    fail "Backend is not reachable at $BASE_URL (is it started? see ./scripts/start.sh)"
fi

# System status (covers DB, ffmpeg/ffprobe, models, from the backend's own view)
STATUS_JSON="$(curl -fsS "$BASE_URL/api/system/status" 2>/dev/null || true)"
if [ -n "$STATUS_JSON" ]; then
    pass "Backend system status endpoint responded"
    echo "$STATUS_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(f\"       FFmpeg:  {d.get('ffmpeg_version') or 'NOT FOUND'}\")
print(f\"       FFprobe: {d.get('ffprobe_version') or 'NOT FOUND'}\")
print(f\"       Models:  {', '.join(d.get('installed_models') or []) or 'none installed'}\")
print(f\"       Disk free: {d.get('disk_free_gb')} GB\")
print(f\"       RAM available: {d.get('ram_available_gb')} GB\")
"
    if ! echo "$STATUS_JSON" | grep -q '"ffmpeg_version":null' ; then :; fi
else
    warn "Could not fetch /api/system/status (backend may be down)"
fi

# Database file
DB_FILE="$ROOT_DIR/data/meetsage.db"
if [ -f "$DB_FILE" ]; then
    pass "Database file exists ($DB_FILE)"
else
    warn "Database file not found yet at $DB_FILE (will be created on first backend start)"
fi

# Storage directories
for d in uploads media transcripts analysis exports models; do
    if [ -d "$ROOT_DIR/data/$d" ]; then
        pass "Storage directory data/$d exists"
    else
        warn "Storage directory data/$d is missing (run scripts/install.sh)"
    fi
done

# FFmpeg / FFprobe on PATH directly (independent of backend)
if command -v ffmpeg >/dev/null 2>&1; then
    pass "ffmpeg on PATH: $(ffmpeg -version | head -1)"
else
    fail "ffmpeg not found on PATH"
fi
if command -v ffprobe >/dev/null 2>&1; then
    pass "ffprobe on PATH: $(ffprobe -version | head -1)"
else
    fail "ffprobe not found on PATH"
fi

# Configuration
if [ -f "$ROOT_DIR/.env" ]; then
    pass ".env configuration file present"
    if ! grep -q "^HUGGINGFACE_TOKEN=." "$ROOT_DIR/.env"; then
        warn "HUGGINGFACE_TOKEN is not set — speaker diarization will fail until configured"
    fi
    if ! grep -q "^LLM_API_KEY=." "$ROOT_DIR/.env"; then
        warn "LLM_API_KEY is not set — meeting analysis will fail until configured (or point LLM_BASE_URL at a keyless local server)"
    fi
else
    fail ".env is missing — copy .env.example to .env"
fi

# Backend venv
if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
    pass "Backend virtual environment present"
else
    fail "Backend virtual environment missing — run scripts/install.sh"
fi

# Disk space
AVAIL_KB=$(df --output=avail "$ROOT_DIR" | tail -1)
AVAIL_GB=$((AVAIL_KB / 1024 / 1024))
if [ "$AVAIL_GB" -lt 2 ]; then
    fail "Only ${AVAIL_GB}GB free disk space — MeetSage needs headroom for models and media"
elif [ "$AVAIL_GB" -lt 5 ]; then
    warn "Only ${AVAIL_GB}GB free disk space — consider freeing space before processing large recordings"
else
    pass "${AVAIL_GB}GB free disk space"
fi

echo
echo "== Summary: $FAILURES failure(s), $WARNINGS warning(s) =="
[ "$FAILURES" -eq 0 ]
