# MeetSage

**Meeting Intelligence Platform** — Capture conversations. Understand what matters. Act on it.

## What is MeetSage?

MeetSage turns audio/video meeting recordings into searchable, structured, actionable
information. It is **not** a graphical wrapper around Whisper — it's a full pipeline:

```
Audio/Video → Media Processing → Transcription → Speaker Diarization →
Structured Transcript → Meeting Analysis (Summary, Decisions, Action Items,
Risks, Dates) → Review / Search / Export
```

The structured transcript is the source of truth. Every piece of derived
intelligence (summary, decisions, action items) keeps a reference back to the
exact transcript segment(s) it came from.

### Why it exists

Meeting recordings are easy to capture and hard to use. MeetSage makes them
searchable and turns rambling conversation into a reviewable record: who said
what, when, what was decided, and what needs to happen next — without sending
your audio anywhere unless you explicitly choose to.

### Local-first design

By default, everything runs on your machine:

```
Recording → Local Whisper (faster-whisper) → Local Transcript → Configured LLM
```

Remote transcription and remote/cloud LLMs are supported but opt-in and clearly
flagged in the UI with a privacy warning before use. See [docs/faq.md](docs/faq.md).

### Multilingual, code-switching support

MeetSage is built for meetings in **English, Hindi, and Telugu**, including
speakers switching languages mid-sentence. The transcript preserves exactly
what was said — it never auto-translates or normalizes to one language. See
[docs/architecture.md](docs/architecture.md#multilingual-transcription) for
how per-segment language tagging actually works (and its known limitation).

## Feature List

- Audio (`.m4a .mp3 .wav .flac .ogg .aac`) and video (`.mp4 .mkv .webm .mov .avi`) upload
- Local transcription via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (tiny → large-v3), CPU/int8 by default
- Configurable remote (OpenAI-compatible Whisper API) transcription providers
- Speaker diarization via [pyannote.audio](https://github.com/pyannote/pyannote-audio), with speaker renaming
- Synchronized audio/video playback with click-to-seek transcript
- Meeting analysis via any OpenAI-compatible LLM: executive summary, key discussion
  points, decisions, action items (owner/due date/priority, conservatively extracted —
  never invented), open issues, risks, important dates, questions
- Long-meeting support via chunked analysis with hierarchical synthesis
- Persistent SQLite-backed job tracking with real per-stage status
- Exports: TXT, SRT, VTT, JSON, Markdown
- Basic full-text search across meetings, transcripts, summaries, and action items
- Settings UI for transcription, diarization, LLM, and remote-provider configuration

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐
│   React UI  │────▶│  FastAPI     │────▶│  SQLite (jobs,     │
│  (Vite/TS)  │◀────│  Backend     │◀────│  meetings, etc.)   │
└─────────────┘     └──────┬───────┘     └───────────────────┘
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                    ▼
  Media Service      Transcription           Diarization
  (ffmpeg/ffprobe)   Provider (local/        (pyannote.audio)
                      remote abstraction)
                            │
                            ▼
                     Analysis Service
                (OpenAI-compatible LLM,
                 chunking + synthesis)
```

Full details: [docs/architecture.md](docs/architecture.md).

## Requirements

- Ubuntu 22.04 or 24.04 (CPU-only; no GPU required)
- Python 3.10+
- Node.js 18+ and npm
- FFmpeg / FFprobe (system-installed; MeetSage never replaces it)
- 8GB+ RAM recommended (see [Performance](docs/troubleshooting.md#slow-transcription-or-diarization))
- A few GB of free disk per downloaded Whisper model

## Quick Start

```
./scripts/install.sh              # checks deps, creates venv, installs everything
./scripts/download_models.sh small # downloads one local Whisper model (~500MB)
./scripts/start.sh                 # starts backend (:8000) and frontend (:5173)
./scripts/health_check.sh          # verifies everything is working
```

Then open **http://localhost:5173**, go to **New Meeting**, upload a recording,
and watch it move through the Jobs page. Once complete, view it under
**Meetings**, with the Transcript and Analysis tabs.

That's dev mode (separate hot-reloading frontend server). For a single-process,
production-style run instead: `./scripts/build_frontend.sh` then
`MEETSAGE_MODE=production ./scripts/start.sh` — see
[docs/deployment.md](docs/deployment.md).

To enable speaker diarization: get a [HuggingFace token](https://huggingface.co/settings/tokens),
accept the license terms on `pyannote/speaker-diarization-3.1`,
`pyannote/segmentation-3.0`, and `pyannote/speaker-diarization-community-1`, then
set `HUGGINGFACE_TOKEN` in `.env`.

To enable meeting analysis: set `LLM_API_KEY` (and `LLM_BASE_URL`/`LLM_MODEL` if
not using OpenAI directly) in `.env`.

## Documentation

| Doc | Covers |
|---|---|
| [docs/installation.md](docs/installation.md) | Full Ubuntu install walkthrough |
| [docs/user-guide.md](docs/user-guide.md) | Using every page/feature of the UI |
| [docs/configuration.md](docs/configuration.md) | Every setting and `.env` variable |
| [docs/architecture.md](docs/architecture.md) | How the system is actually built |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Diagnosing real failure modes |
| [docs/development.md](docs/development.md) | Contributing / extending MeetSage |
| [docs/deployment.md](docs/deployment.md) | Running it beyond a dev laptop |
| [docs/backup-recovery.md](docs/backup-recovery.md) | What to back up and how to restore |
| [docs/faq.md](docs/faq.md) | Common questions |

## Known Limitations

- Per-segment language tagging is a **best-effort heuristic** (dominant Unicode
  script in the segment text), not a verified language-ID model — see
  [docs/architecture.md](docs/architecture.md#multilingual-transcription).
- Diarization and long-recording transcription are CPU-bound and can be slow
  (tens of minutes for hour-plus recordings) on modest hardware — see
  [docs/troubleshooting.md](docs/troubleshooting.md#slow-transcription-or-diarization).
- Diarization can leave a meaningful fraction of segments unassigned to any
  speaker (pyannote's own segmentation misses some real speech, confirmed on a
  real recording) — see
  [docs/troubleshooting.md](docs/troubleshooting.md#some-transcript-segments-have-no-speaker-label).
- Search is LIKE-based, not a full-text index (by design, meant to be swapped
  in later — see spec section 27 / architecture docs).
- Frontend tests are component-level (Vitest + Testing Library), not full
  browser end-to-end automation — see
  [docs/development.md](docs/development.md#frontend-testing).

## License

Internal project — no license file included yet.
