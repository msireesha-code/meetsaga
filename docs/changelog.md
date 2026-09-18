# Changelog

## Unreleased

Initial implementation of MeetSage.

### Added
- Media pipeline: upload validation, ffprobe metadata, ffmpeg audio extraction/normalization
- Local transcription via faster-whisper (tiny/base/small/medium/large-v3), CPU/int8
- Remote transcription provider abstraction (OpenAI-compatible HTTP endpoint)
- Per-segment language tagging (English/Hindi/Telugu via Unicode script detection)
- Speaker diarization via pyannote.audio 4.x, with speaker renaming
- Synchronized audio/video playback with click-to-seek transcript
- Meeting analysis via any OpenAI-compatible LLM: summary, key discussion points,
  decisions, action items (conservative extraction), open issues, risks, dates, questions
- Chunked analysis with hierarchical summary synthesis for long meetings
- Persistent SQLite-backed job tracking with real transcription progress reporting
- Fault-tolerant pipeline: diarization/analysis failures don't discard a completed transcript
- Exports: TXT, SRT, VTT, JSON, Markdown (reflecting renamed speakers)
- Basic search across meetings, transcripts, summaries, action items, speakers
- Settings UI: transcription, remote providers (with connection testing), diarization,
  LLM configuration, local model management
- Dashboard, Jobs, Meetings, Meeting detail (Overview/Transcript/Analysis/Action Items/Exports), Search pages
- Lifecycle scripts: install/start/stop/health_check/download_models/build_frontend
- Automated test suite (pytest): security validation, no-hallucination policy,
  pipeline fault tolerance, export/search correctness
- Frontend test suite (Vitest + Testing Library): component rendering, speaker
  rename resolution, API error handling
- Alembic-managed database schema migrations, with automatic baseline
  detection/stamping for pre-migration installs
- Production mode (`MEETSAGE_MODE=production`): backend serves the built
  frontend on the same origin (one process, no CORS), with systemd unit and
  nginx reverse-proxy examples under `deploy/`
- Configurable CORS origins (`CORS_ALLOWED_ORIGINS`)

### Known Limitations (see README.md for the full list)
- Per-segment language tagging is heuristic, not a verified language-ID model
- Frontend tests are component-level, not full browser end-to-end automation
- Search is LIKE-based, not a full-text index
