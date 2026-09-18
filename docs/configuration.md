# Configuration Reference

MeetSage is configured through two layers:

1. **`.env`** (backend startup-time config: storage paths, default provider,
   secrets). Read once when the backend process starts — changing `.env`
   requires a restart (`./scripts/stop.sh && ./scripts/start.sh`).
2. **Settings UI / `AppSetting` table** (runtime-editable config: default
   language set, remote provider list, LLM model/temperature, etc.) — no
   restart needed.

Never commit a real `.env` — only `.env.example` (with placeholders) is
tracked in git.

## Environment Variables (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `MeetSage` | Display name |
| `DATA_DIR` | `./data` | Root of all storage (uploads/media/transcripts/analysis/exports/models/db) |
| `DATABASE_URL` | `sqlite:///./data/meetsage.db` | SQLite connection string — only the **filename** is actually used; the file always lives under `DATA_DIR` regardless of any directory you put here (change `DATA_DIR` to move it) |
| `DEFAULT_ANALYSIS_LANGUAGE` | `en` | Default analysis output language |
| `DEFAULT_TRANSCRIPTION_PROVIDER` | `local` | Default provider shown in New Meeting |
| `LOCAL_WHISPER_MODEL` | `small` | Default local model |
| `LOCAL_WHISPER_DEVICE` | `cpu` | faster-whisper device |
| `LOCAL_WHISPER_COMPUTE_TYPE` | `int8` | faster-whisper compute type (int8 recommended for CPU) |
| `LOCAL_WHISPER_CPU_THREADS` | `0` | `0` = let ctranslate2 auto-select thread count |
| `MAX_CONCURRENT_JOBS` | `1` | Size of the background job thread pool |
| `DIARIZATION_ENABLED` | `true` | Default diarization toggle for new meetings |
| `HUGGINGFACE_TOKEN` | *(empty)* | Required for diarization — see [installation.md](installation.md#7-model-installation) |
| `LLM_PROVIDER` | `openai-compatible` | Currently the only supported analysis provider type |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible chat completions endpoint |
| `LLM_API_KEY` | *(empty)* | Required if `LLM_BASE_URL` is the real OpenAI API; optional for a keyless local server |
| `LLM_MODEL` | `gpt-4o-mini` | Model name passed to the endpoint |
| `LLM_TEMPERATURE` | `0.2` | Lower = more conservative/consistent extraction |
| `LLM_MAX_TOKENS` | `2000` | Per-request completion token cap |
| `LLM_TIMEOUT_SECONDS` | `120` | Per-request timeout |
| `MAX_UPLOAD_SIZE_MB` | `2048` | Upload size limit |

## Local Transcription

```
Provider: Local Model
Model: small
Device: CPU
Compute Type: int8
```

Configurable in Settings → Transcription, or per-meeting in New Meeting
(model override only; device/compute type are process-wide `.env` settings).

## Remote Transcription

Configured in Settings → Remote Transcription Providers (stored in the
`remote_providers` table, not `.env`):

```
Provider Name:   Office Whisper
Base URL:        https://whisper.example.internal
Endpoint Path:   /v1/audio/transcriptions
Model:           whisper-large-v3
API Token:       ••••••••          (masked in UI, never returned by the API)
Auth Method:     bearer
Connect Timeout: 10s
Read Timeout:    300s
Total Timeout:   600s
TLS Verification: enabled
```

Never use real credentials in documentation or examples — the placeholders
above are illustrative only. Use **Test Connection** in Settings to verify
reachability (`GET /v1/models`) before relying on a provider.

## LLM / Analysis

Any OpenAI-compatible chat completions endpoint works — real OpenAI, a
local server (Ollama, LM Studio, vLLM with an OpenAI-compatible shim), or an
office-hosted proxy. Example local config:

```
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=not-required
LLM_MODEL=llama3.1:8b
```

Transcription and analysis providers are fully independent — you can mix
local Whisper with a remote LLM, or remote Whisper with a local LLM, in any
combination.

## Languages

Registry is currently fixed in code (`app/config.py: SUPPORTED_LANGUAGES`):

```python
SUPPORTED_LANGUAGES = {"en": "English", "hi": "Hindi", "te": "Telugu"}
```

See [development.md](development.md#adding-a-language) for how to add one.

## Storage Layout

```
data/
├── meetsage.db     SQLite database
├── uploads/        original uploaded files (renamed internally, never overwritten)
├── media/          extracted/normalized 16kHz mono WAV per meeting
├── transcripts/     (reserved — transcript data currently lives in the DB, not files)
├── analysis/        (reserved — analysis data currently lives in the DB, not files)
├── exports/         (reserved — exports are generated on demand and streamed, not cached here)
├── models/         downloaded faster-whisper model files
├── run/            PID files for scripts/start.sh & stop.sh
└── logs/           backend.log, frontend.log
```

Note: transcript/analysis/export data is stored in the SQLite database, not as
separate files under `data/transcripts` etc. — those directories exist for
future use (e.g. caching generated exports) but aren't populated yet. Back up
`data/meetsage.db` together with `data/uploads` and `data/media` (see
[backup-recovery.md](backup-recovery.md)).
