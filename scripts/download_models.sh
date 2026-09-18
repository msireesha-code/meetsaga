#!/usr/bin/env bash
# Downloads one local Whisper model for offline transcription.
# Usage: ./scripts/download_models.sh [tiny|base|small|medium|large-v3]
# Does NOT download all models automatically — only the one requested (default: small).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
MODEL="${1:-small}"

VALID_MODELS="tiny base small medium large-v3"
if ! echo "$VALID_MODELS" | grep -qw "$MODEL"; then
    echo "Unknown model '$MODEL'. Valid options: $VALID_MODELS" >&2
    exit 1
fi

if [ ! -x "$BACKEND_DIR/venv/bin/python" ]; then
    echo "Backend virtual environment not found — run scripts/install.sh first." >&2
    exit 1
fi

echo "Downloading faster-whisper model '$MODEL' into data/models/ ..."
mkdir -p "$ROOT_DIR/data/models"

# shellcheck disable=SC1091
source "$BACKEND_DIR/venv/bin/activate"
python3 - "$MODEL" "$ROOT_DIR/data/models" <<'PYEOF'
import sys
from faster_whisper import WhisperModel

model_name, download_root = sys.argv[1], sys.argv[2]
print(f"Loading (and downloading if needed) '{model_name}'...")
WhisperModel(model_name, device="cpu", compute_type="int8", download_root=download_root)
print("Done.")
PYEOF
deactivate

echo "Model '$MODEL' is ready. Select it in Settings > Transcription, or in New Meeting."
