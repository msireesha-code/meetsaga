# Installation Guide

Target environment: Ubuntu 22.04 or 24.04, CPU-only, no GPU required.

## System Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16 GB+ |
| Disk | 10 GB free | 30 GB+ free (models + media add up) |

RAM matters more than the table suggests: transcription and diarization are
CPU/memory heavy, and if your system swaps (RAM exhausted), processing that
would normally take a few minutes can take 20-30+ minutes. Close memory-heavy
applications (browsers with many tabs, etc.) before processing long recordings.

## 1. Verify Your Environment

```bash
lsb_release -a
python3 --version      # need 3.10+
node --version          # need 18+
npm --version
ffmpeg -version
ffprobe -version
```

If `ffmpeg`/`ffprobe` are missing:

```bash
sudo apt update
sudo apt install ffmpeg
```

MeetSage detects and uses whatever FFmpeg/FFprobe is already on `PATH`. It
never downloads, replaces, or upgrades your system FFmpeg.

## 2. Install Dependencies

```bash
sudo apt install python3 python3-venv python3-pip
# Node.js: use your distro package, nodesource, or nvm — any 18+ works.
```

## 3. Run the Installer

From the repository root:

```bash
./scripts/install.sh
```

This script:

1. Checks OS, Python, Node/npm, FFmpeg/FFprobe.
2. Creates `backend/venv` (a Python virtualenv with `--system-site-packages`,
   so it reuses any already-installed `torch`/`fastapi`/etc. rather than
   re-downloading them).
3. Installs backend dependencies from `requirements.txt`.
4. Installs frontend dependencies (`npm install`).
5. Creates `data/{uploads,media,transcripts,analysis,exports,models,run,logs}`.
6. Initializes the SQLite database schema (never overwrites existing data).
7. Copies `.env.example` to `.env` if `.env` doesn't already exist.
8. Validates the install and prints next steps.

It is safe to re-run — it will not overwrite an existing `venv`, `.env`, or
your data directory.

It will **not**: replace FFmpeg, download any Whisper model automatically, or
expose secrets.

## 4. Python Virtual Environment (what install.sh does, for reference)

```bash
python3 -m venv --system-site-packages backend/venv
source backend/venv/bin/activate
pip install -r requirements.txt
deactivate
```

## 5. Backend Installation (manual equivalent)

```bash
cd backend
source venv/bin/activate
python -c "from app.database import init_db; init_db()"
deactivate
```

## 6. Frontend Installation (manual equivalent)

```bash
cd frontend
npm install
```

## 7. Model Installation

MeetSage does not download any Whisper model until you ask for one. Available
models (accuracy and resource use increase down the list):

| Model | Approx. download size | Notes |
|---|---|---|
| tiny | ~75 MB | Fast, lower accuracy |
| base | ~150 MB | |
| small | ~500 MB | **Default** — good balance for CPU |
| medium | ~1.5 GB | Noticeably slower on CPU |
| large-v3 | ~3 GB | Best accuracy, slow on CPU-only hardware |

Download one:

```bash
./scripts/download_models.sh small
```

Or manage models from the UI: **Settings → Local Models** (list installed
models, download, delete).

### Speaker diarization models (optional)

Diarization uses `pyannote/speaker-diarization-3.1` from HuggingFace, which is
gated (requires accepting license terms, not just a token):

1. Create a token at https://huggingface.co/settings/tokens
2. Accept the license on **all three** of these model pages (pyannote-audio 4.x
   pulls in a community dependency the older versions didn't need):
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
   - https://huggingface.co/pyannote/speaker-diarization-community-1
3. Set `HUGGINGFACE_TOKEN=hf_...` in `.env`.

If you skip this, transcription/analysis still work fully — diarization simply
fails gracefully per-job (see [architecture.md](architecture.md#diarization)).

## 8. First Startup

```bash
./scripts/start.sh
```

This starts the backend (`uvicorn`, default port 8000) and frontend (`vite`,
default port 5173) as background processes, with PID files under `data/run/`
and logs under `data/logs/`. Override ports with environment variables:

```bash
MEETSAGE_BACKEND_PORT=9000 MEETSAGE_FRONTEND_PORT=3000 ./scripts/start.sh
```

Stop everything with `./scripts/stop.sh`.

## 9. Health Check

```bash
./scripts/health_check.sh
```

Prints `PASS`/`WARN`/`FAIL` for: backend reachability, database, storage
directories, FFmpeg/FFprobe, `.env` presence (and whether HF/LLM keys look
configured), venv presence, and free disk space. Exits non-zero if anything
`FAIL`s — safe to use in a monitoring script or CI smoke test.

## 10. Accessing the UI

Open the URL `start.sh` prints — by default **http://localhost:5173**. The
backend API (and interactive docs) is at **http://localhost:8000/docs**.

If you changed `MEETSAGE_FRONTEND_PORT`/`MEETSAGE_BACKEND_PORT`, use those
instead.
