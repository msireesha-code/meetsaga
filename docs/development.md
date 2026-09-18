# Development Guide

## Repository Structure

```
meetsage/
├── backend/
│   ├── app/            FastAPI application (see architecture.md)
│   ├── tests/          pytest suite
│   ├── alembic/         Schema migrations (versions/, env.py)
│   ├── venv/           Python virtualenv (not committed)
│   ├── alembic.ini
│   └── pytest.ini
├── frontend/
│   ├── src/{pages,components,services,types,test}/  (*.test.tsx next to what they test)
│   ├── dist/            Production build output (not committed; scripts/build_frontend.sh)
│   └── package.json
├── data/                All runtime storage (not committed, except .gitkeep)
├── scripts/             install/start/stop/health_check/download_models/build_frontend
├── deploy/              systemd unit + nginx config examples for production deployment
├── docs/                This documentation set
├── requirements.txt
├── .env.example
└── README.md
```

## Development Setup

```bash
./scripts/install.sh
source backend/venv/bin/activate   # for backend work
```

Run backend and frontend separately during development instead of via
`scripts/start.sh` if you want live reload output in your terminal:

```bash
# terminal 1
cd backend && source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend && npm run dev
```

## Backend Development

- Config: `app/config.py` (`Settings`, via `pydantic-settings`, reads `.env`).
- New endpoints: add a router in `app/api/`, include it in `app/main.py`.
- New DB fields: add to the SQLAlchemy model in `app/models/entities.py`, then
  generate and apply an Alembic migration (see below). Don't edit
  `data/meetsage.db`'s schema by hand.

## Frontend Development

- API calls go through `frontend/src/services/api.ts` — a thin typed `fetch`
  wrapper, not a generated client. Types in `frontend/src/types/index.ts` are
  hand-kept in sync with `backend/app/schemas.py` (no shared codegen yet).
- New pages: add to `frontend/src/pages/`, wire a route in `App.tsx`, add a nav
  link in `components/Nav.tsx` if it belongs in the primary navigation.
- Type-check before committing: `cd frontend && npx tsc --noEmit`.
- Production build check: `npm run build`.

## Testing

```bash
cd backend
source venv/bin/activate
python -m pytest            # full suite
python -m pytest -k job_pipeline   # just one area
```

Tests use an isolated temp SQLite database (set up in `tests/conftest.py`
before any app module is imported) — they never touch your real
`data/meetsage.db`. External services (LLM, diarization, transcription model)
are mocked in most tests for speed and determinism; a few tests that exercise
real `ffmpeg`/`ffprobe` on tiny synthetic clips are intentionally not mocked,
since that's fast and deterministic in practice.

Test files and what they cover:

| File | Covers |
|---|---|
| `test_media_validation.py` | Filename sanitization, extension/size validation |
| `test_language_id.py` | Unicode-script language tagging |
| `test_chunking.py` | Transcript chunking for long-meeting analysis |
| `test_export_formats.py` | TXT/SRT/VTT/JSON/MD renderers |
| `test_analysis_openai_compatible.py` | No-hallucination policy, JSON parsing, multi-chunk merging |
| `test_job_pipeline.py` | Full pipeline orchestration, fault tolerance of diarization/analysis failures |
| `test_api_meetings.py` | Upload security (path traversal, extension/size validation) |
| `test_api_settings_exports_search.py` | Token masking, exports reflect speaker renames, search |

### Frontend Testing

```bash
cd frontend
npm test              # vitest run — component/service tests, jsdom environment
npx tsc --noEmit       # type-check (also run automatically by `npm run build`)
```

Uses Vitest + React Testing Library (config in `vite.config.ts`, setup in
`src/test/setup.ts`). Test files sit next to what they test
(`Component.test.tsx`). No end-to-end/browser test suite exists — these are
component-level tests with mocked `fetch`, not full-page browser automation.

| File | Covers |
|---|---|
| `components/StatusBadge.test.tsx` | Status → badge style mapping |
| `components/ActionItemsTable.test.tsx` | "Not specified" rendering, priority styling, timestamp navigation (via source segment vs. string fallback) |
| `components/TranscriptView.test.tsx` | Renamed speakers shown in the transcript itself, empty state, audio vs. video element selection |
| `services/api.test.ts` | Error handling (detail message vs. statusText fallback), FormData vs. JSON Content-Type handling |
| `pages/Search.test.tsx` | No search-on-empty-input, rendering results per category, no-results state |

## Linting / Formatting

No linter/formatter is currently configured for the backend. For the
frontend, TypeScript's own compiler (`tsc --noEmit`) is the only enforced
check; ESLint config from the Vite template exists but isn't wired into CI.

## Debugging

- Backend: logs go to stdout (`data/logs/backend.log` when started via
  `scripts/start.sh`); secrets are redacted by `app/logging_config.py` but
  never rely on that alone — don't log request bodies containing tokens.
- A specific job's full lifecycle: `GET /api/jobs/{job_id}` and
  `GET /api/meetings/{meeting_id}/job` (latest job for a meeting).
- Interactive API exploration: http://localhost:8000/docs

## Database Migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/),
configured in `backend/alembic/` (`env.py` is wired to reuse the app's own
`Settings`/`.env`-derived engine URL and `Base.metadata` — no separate
connection string to keep in sync).

**After changing a model** in `app/models/entities.py`:

```bash
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "describe the change"
```

Then **review the generated file** under `backend/alembic/versions/` —
autogenerate is a good first draft, not a guarantee (it won't detect every
kind of change, e.g. some constraint renames). Apply it:

```bash
alembic upgrade head
```

`./scripts/install.sh` runs `alembic upgrade head` automatically on both fresh
installs and upgrades. Tests (`backend/tests/conftest.py`) deliberately keep
using `Base.metadata.create_all()` against a throwaway temp SQLite file
instead of running migrations — this keeps the test suite fast and immune to
migration ordering issues, and is safe specifically *because* both paths are
generated from the same `Base.metadata`, so the resulting schema is identical
either way. If you ever suspect the two have drifted, run
`alembic check` (compares live models against the current migration head).

**Upgrading a pre-Alembic MeetSage install** (a database created before this
was introduced, with tables but no `alembic_version` row): `./scripts/install.sh`
detects this automatically and runs `alembic stamp head` instead of
`upgrade head`, marking the existing schema as current without re-running (and
failing on) `CREATE TABLE` for tables that already exist. See
[backup-recovery.md](backup-recovery.md#upgrade-procedure).

## Adding a Transcription Provider

1. Implement `TranscriptionProvider` (see `app/services/transcription/base.py`)
   in a new file under `app/services/transcription/`.
2. Wire it into `app/services/transcription/registry.py::build_provider` (for
   a remote-style provider, likely alongside the existing `RemoteProvider` DB
   row lookup; for a new local-style provider, add a `provider_name` branch).
3. No other module should need to change — `job_runner.py` and the API layer
   only ever call through `build_provider(...)`.
4. Add tests mirroring `test_analysis_openai_compatible.py`'s approach: mock
   the actual network/model call, assert on the `TranscriptionResult` shape.

## Adding a Language

1. Add the code/name pair to `SUPPORTED_LANGUAGES` in `app/config.py`.
2. If the language uses a distinct Unicode script, add a detection pattern in
   `app/services/transcription/language_id.py::detect_segment_language`
   (mirror the existing Devanagari/Telugu regex approach).
3. Add the language to `SUPPORTED_LANGS` in
   `frontend/src/pages/NewMeeting.tsx` and `LANGUAGE_NAMES` in
   `frontend/src/types/index.ts`.
4. No transcription-provider code changes needed — faster-whisper already
   supports far more languages than are currently exposed in the UI; this is
   purely a registry/UI change.

## Adding an Analysis Module

New analysis fields (beyond summary/decisions/action items/open issues/
risks/dates/questions) require: extending `AnalysisResult` in
`app/services/analysis/base.py`, the prompt schema in
`app/services/analysis/prompts.py`, the `Analysis` SQLAlchemy model, the
`AnalysisOut` Pydantic schema, the merge logic in
`openai_compatible.py::analyze()`, and the corresponding UI section in
`frontend/src/pages/MeetingDetail.tsx`.

## Adding an Export Format

Add a pure function to `app/services/export/formats.py` (input: plain dicts,
output: a string — no I/O, so it stays trivially unit-testable), register its
media type and the format name in `app/api/exports.py`, and add a button in
the Exports tab of `frontend/src/pages/MeetingDetail.tsx`.

## Adding an API Endpoint

Add a route to the relevant router in `app/api/`, or create a new router file
and `app.include_router(...)` it in `app/main.py`. Use `Depends(get_db)` for a
DB session (see any existing router for the pattern) — don't construct a
session manually inside a request handler.
