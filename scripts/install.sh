#!/usr/bin/env bash
# MeetSage installer for Ubuntu 24.04 (also verified on 22.04).
#
# This script does NOT:
#   - replace or upgrade the system FFmpeg/FFprobe
#   - download any Whisper models (use scripts/download_models.sh for that)
#   - overwrite existing user data under data/
#   - print or persist any secrets
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

pass() { echo "  [PASS] $1"; }
warn() { echo "  [WARN] $1"; }
fail() { echo "  [FAIL] $1"; exit 1; }

echo "== MeetSage Installer =="

echo "1. Checking OS..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "${ID:-}" = "ubuntu" ]; then
        pass "Ubuntu detected ($VERSION_ID)"
        [ "${VERSION_ID%%.*}" -lt 22 ] && warn "MeetSage targets Ubuntu 22.04/24.04; older versions are unverified."
    else
        warn "Non-Ubuntu OS detected ($ID). MeetSage may still work, but is only verified on Ubuntu."
    fi
else
    warn "Could not detect OS."
fi

echo "2. Checking Python..."
if command -v python3 >/dev/null 2>&1; then
    PY_VERSION=$(python3 --version | awk '{print $2}')
    pass "python3 found ($PY_VERSION)"
else
    fail "python3 not found. Install it with: sudo apt install python3 python3-venv python3-pip"
fi

echo "3. Checking Node.js / npm..."
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    pass "node $(node --version), npm $(npm --version) found"
else
    fail "node/npm not found. Install Node.js 18+ (e.g. via nodesource or nvm)."
fi

echo "4. Checking FFmpeg / FFprobe (existing system installation, never replaced)..."
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
    pass "ffmpeg: $(ffmpeg -version | head -1)"
    pass "ffprobe: $(ffprobe -version | head -1)"
else
    fail "ffmpeg/ffprobe not found. Install with: sudo apt install ffmpeg"
fi

echo "5. Creating Python virtual environment..."
if [ -d "$BACKEND_DIR/venv" ]; then
    warn "venv already exists at backend/venv — leaving it in place. Delete it manually to force a clean rebuild."
else
    python3 -m venv --system-site-packages "$BACKEND_DIR/venv"
    pass "Created backend/venv"
fi

echo "6. Installing backend dependencies (this can take a while the first time)..."
# shellcheck disable=SC1091
source "$BACKEND_DIR/venv/bin/activate"
pip install --upgrade pip -q
pip install -r "$ROOT_DIR/requirements.txt" -q
deactivate
pass "Backend dependencies installed"

echo "7. Installing frontend dependencies..."
(cd "$FRONTEND_DIR" && npm install --silent)
pass "Frontend dependencies installed"

echo "8. Creating data directories..."
mkdir -p "$ROOT_DIR"/data/{uploads,media,transcripts,analysis,exports,models,run,logs}
pass "Data directories ready under data/"

echo "9. Initializing database schema (via Alembic migrations)..."
# shellcheck disable=SC1091
source "$BACKEND_DIR/venv/bin/activate"
(
    cd "$BACKEND_DIR"
    HAS_ALEMBIC_VERSION=$(python3 -c "
from app.database import engine
from sqlalchemy import inspect
print('yes' if 'alembic_version' in inspect(engine).get_table_names() else 'no')
")
    HAS_APP_TABLES=$(python3 -c "
from app.database import engine
from sqlalchemy import inspect
print('yes' if 'meetings' in inspect(engine).get_table_names() else 'no')
")
    if [ "$HAS_ALEMBIC_VERSION" = "yes" ]; then
        alembic upgrade head
    elif [ "$HAS_APP_TABLES" = "yes" ]; then
        # Existing database from before migrations were introduced: the schema
        # already matches the baseline migration, so record that instead of
        # re-running (and failing on) CREATE TABLE for tables that already exist.
        echo "Existing pre-Alembic database detected — stamping baseline revision (no data touched)."
        alembic stamp head
    else
        alembic upgrade head
    fi
)
deactivate
pass "Database schema up to date (never overwrites existing data)"

echo "10. Checking .env..."
if [ -f "$ROOT_DIR/.env" ]; then
    warn ".env already exists — leaving your existing configuration untouched."
else
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    pass "Created .env from .env.example — edit it to configure remote transcription, HuggingFace token, or an LLM."
fi

echo "11. Validating installation..."
[ -x "$BACKEND_DIR/venv/bin/python" ] || fail "Backend venv python missing"
[ -d "$FRONTEND_DIR/node_modules" ] || fail "Frontend node_modules missing"
pass "Installation looks valid"

cat <<EOF

== Install complete ==

Next steps:
  1. (Optional) Edit .env — set HUGGINGFACE_TOKEN for speaker diarization,
     and LLM_API_KEY / LLM_BASE_URL for meeting analysis.
  2. Download a local Whisper model:   ./scripts/download_models.sh small
  3. Start MeetSage:                   ./scripts/start.sh
  4. Check everything is healthy:      ./scripts/health_check.sh
  5. Open the UI at the URL start.sh prints (default http://localhost:5173)
EOF
