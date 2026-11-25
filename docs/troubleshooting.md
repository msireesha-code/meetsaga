# Troubleshooting

## MeetSage won't start

```bash
./scripts/health_check.sh
tail -50 data/logs/backend.log
tail -50 data/logs/frontend.log
```

Common causes: `.env` missing (`cp .env.example .env`), venv missing
(`./scripts/install.sh`), or a port already in use (see below).

## Backend unavailable

```bash
curl -sS http://127.0.0.1:8000/api/system/health
cat data/run/backend.pid   # if present, check the PID is actually alive:
kill -0 "$(cat data/run/backend.pid)"; echo $?   # 0 = alive
tail -100 data/logs/backend.log
```

If a stale PID file exists but nothing's running, `./scripts/stop.sh` (removes
stale files) then `./scripts/start.sh` again.

Port already in use:

```bash
ss -ltnp | grep 8000
```

Set a different port: `MEETSAGE_BACKEND_PORT=8001 ./scripts/start.sh`.

## Frontend unavailable

Same idea as above with `data/logs/frontend.log` and port 5173. Note: `npm run
dev` spawns a child `vite` process — if you ever kill the frontend manually
rather than via `./scripts/stop.sh`, make sure to kill the actual `vite`
process too (`pgrep -af vite`), not just the `npm` wrapper, or it'll keep
holding the port.

### Frontend fails with `ERR_MODULE_NOT_FOUND ... node_modules/dist/node/cli.js`

`start.sh` reports `Frontend failed to start`, and `data/logs/frontend.log`
shows:

```
Error [ERR_MODULE_NOT_FOUND]: Cannot find module
'.../frontend/node_modules/dist/node/cli.js' imported from
.../frontend/node_modules/.bin/vite
```

Cause: the entries in `frontend/node_modules/.bin/` are plain file copies
instead of symlinks (this happens when `node_modules` is copied, synced, or
extracted with a tool that doesn't preserve symlinks). The copied `vite`
script resolves its relative imports from `.bin/` rather than from
`node_modules/vite/bin/`, so it can't find its own code. Plain `npm install`
does not fix it because npm considers the packages already installed.

Check: `ls -la frontend/node_modules/.bin/vite` should show a symlink
(`-> ../vite/bin/vite.js`), not a regular file.

Fix — recreate the bin links, then start again:

```bash
cd frontend
rm -rf node_modules/.bin
npm rebuild
cd ..
./scripts/start.sh
```

(Deleting `frontend/node_modules` entirely and running `npm install` also
works, but takes longer.)

## FFmpeg missing / FFprobe missing

```bash
which ffmpeg ffprobe
sudo apt install ffmpeg
```

MeetSage does not bundle or install FFmpeg itself — it only detects and uses
what's on `PATH`.

## Model download failure

```bash
./scripts/download_models.sh small
```

If it fails: check internet connectivity and disk space
(`df -h .`), then check the traceback — a corrupted partial download can
sometimes require clearing the specific model's folder under `data/models/`
and retrying.

## Slow transcription or diarization

This is the most common real-world friction point. Both are CPU-bound and
memory-hungry:

- **Check RAM/swap pressure**: `free -h`. If swap is near full, everything
  slows down dramatically (observed: an 18-minute recording that should take a
  few minutes can take 20-30+ minutes under swap pressure). Close other
  memory-heavy applications before processing long recordings.
- **Check it's actually working, not hung**: `ps aux --sort=-%cpu | head -5` —
  if the `uvicorn` process is using a large percentage of CPU, it's actively
  computing.
- **Use a smaller model** for faster (lower-accuracy) transcription:
  Settings → Transcription → Local Model → `tiny` or `base`.
- **Real-time factor** varies a lot by hardware; there's no fixed number to
  expect. Diarization in particular runs multiple neural-network passes
  (segmentation, embedding, clustering) over the whole recording and is
  typically the slowest single stage on CPU-only hardware for long recordings.
- The Jobs page shows real (not fabricated) progress during transcription,
  based on audio position actually processed — if it's moving, it's working.

## Transcript is missing chunks of what was actually said

Confirmed root cause (2026-09-09): faster-whisper's voice-activity detection
(`vad_filter`) can misclassify real speech as silence and silently drop it —
on a real recording it skipped ~12 continuous seconds of dialogue mid-segment.
This is now fixed: local transcription always runs with `vad_filter=False`
(see `app/services/transcription/local_provider.py`), relying on
faster-whisper's own `no_speech_threshold` to skip genuine silence instead of
VAD's coarser cut. If you still see gaps after this fix:

- Compare segment `end` of one row to `start` of the next in the transcript —
  a gap of more than a couple seconds during otherwise continuous speech is
  the symptom to look for.
- Try a larger model (`medium`/`large-v3`) — accuracy on fast or overlapping
  speech improves noticeably over `tiny`/`small`.
- Re-transcribe: there is no one-click "retranscribe only" action yet in the
  UI, but re-uploading the same file processes it fresh with the current
  (fixed) settings.

## High CPU usage / Memory exhaustion

Expected during transcription/diarization/analysis of long recordings — see
above. If the machine becomes unresponsive, lower `MAX_CONCURRENT_JOBS` to `1`
(already the default) and use a smaller Whisper model.

## Poor Hindi / Telugu transcription

- Confirm the language is checked in "Expected Languages" for that meeting.
- Try a larger model (`medium`/`large-v3`) — `tiny`/`base` are noticeably
  weaker on non-English speech.
- Background noise and overlapping speech degrade all languages, but
  disproportionately affect the less-resourced ones in Whisper's training data.

## Mixed-language transcription problems

MeetSage never merges or translates languages — if the transcript text looks
wrong, that's a transcription accuracy issue, not a design limitation. However,
the per-segment **`language` tag** is a best-effort heuristic (dominant Unicode
script in the segment's text — see
[architecture.md](architecture.md#multilingual-transcription)), not a
verified language-ID model. A segment that's mostly English with a couple of
Hindi words will be tagged `en`; this is expected, not a bug. If you need
finer-grained (per-word) language attribution, that would require a different
approach and isn't implemented in this version.

## Diarization failure

Check the job's error message on the Jobs page — the two most common causes
observed in practice:

1. **Gated model access (HTTP 403)**: `HUGGINGFACE_TOKEN` is valid but the
   license hasn't been accepted on all three required model pages. See
   [installation.md](installation.md#7-model-installation) — this needs
   `pyannote/speaker-diarization-3.1`, `pyannote/segmentation-3.0`, **and**
   `pyannote/speaker-diarization-community-1` (a 4.x dependency).
2. **No token configured at all**: set `HUGGINGFACE_TOKEN` in `.env` and
   restart the backend.

Either way, the job still completes with the transcript intact — retry
diarization alone from the meeting's Analysis tab ("Retry Diarization") once
fixed, without re-transcribing.

## Some transcript segments have no speaker label

Confirmed on a real meeting (2026-09-10): pyannote's diarization pipeline can
fail to detect speech at all in some windows — not a boundary/overlap-matching
bug in `assign_speakers_to_segments`, but pyannote's own segmentation model
finding zero speaker activity in a stretch where Whisper correctly transcribed
real speech (verified: one recording had a contiguous 17-second span with no
detected speaker turns from either party, despite continuous dialogue).

Investigated and ruled out: passing `min_speakers`/`max_speakers` hints to the
pipeline (even with the correct, user-confirmed speaker count) made **no
difference** — identical turns, same gap — because those hints only affect the
clustering stage, which runs after segmentation; they can't recover speech the
segmentation stage never flagged as active. `pyannote/speaker-diarization-3.1`
does not expose a segmentation sensitivity/VAD threshold as a pipeline
parameter in the installed version (only `clustering.threshold`,
`clustering.min_cluster_size`, and `segmentation.min_duration_off` are
configurable — none of which affect the segmentation model's own confidence).

A transcript segment left without a speaker label is intentional in this
situation — MeetSage never guesses a speaker when there's no detected overlap
(see [architecture.md](architecture.md#diarization)) — but be aware that in
recordings with quiet speakers, cross-talk, or background noise, a meaningful
fraction of segments (observed: ~21% on one real call) may end up unassigned
for this reason. There's no user-facing workaround today; a fix would require
either a different/more sensitive segmentation model or directly overriding
its internal binarization thresholds, which isn't exposed by this pipeline
version.

## Remote Whisper connection failure

Use **Settings → Remote Transcription Providers → Test Connection** first. If
it fails: check the base URL/endpoint path, that the server is reachable from
the machine running the MeetSage backend (not your browser — remote calls are
backend-side), and TLS verification settings if using a self-signed cert.

## Authentication failure (remote Whisper or LLM)

- Remote Whisper: check the API token and auth method in Settings match what
  the server expects (`Authorization: Bearer <token>` by default).
- LLM: MeetSage refuses to call the real OpenAI API with an empty/placeholder
  key up front, with a clear error like:
  *"No LLM API key configured. Set LLM_API_KEY in .env..."* — a raw 401 from
  the endpoint itself means the key is present but wrong/revoked.

## TLS failure

If a remote provider uses a self-signed or internal CA certificate, either
install that CA in the system trust store, or (only for trusted internal
networks) disable `TLS Verification` for that specific provider in Settings.
Never disable it for a public-internet endpoint.

## LLM failure

Shown on the meeting (job stays `COMPLETED`, with the error recorded — see
[architecture.md](architecture.md#job-processing)). Use **Re-run Analysis**
after fixing the configuration. Check `data/logs/backend.log` for the
specific HTTP status/error from the LLM endpoint (API keys/tokens are never
logged, even in errors).

## Context-length failure

Long meetings are automatically chunked before analysis (see
[architecture.md](architecture.md#analysis)); if you still hit a context-length
error, your `LLM_MAX_TOKENS` or the endpoint's own context window may be
smaller than expected for the model you configured — check the model's actual
context window and adjust `LLM_MAX_TOKENS`/the chunk size if needed.

## Video processing failure

Check `ffprobe`/`ffmpeg` can read the file directly:

```bash
ffprobe -v error -show_format -show_streams your_file.mp4
```

A codec ffprobe can't parse (unusual/corrupt container) will fail the
`MEDIA_ANALYSIS` stage with a clear error rather than silently producing bad
output.

## Insufficient disk space

`./scripts/health_check.sh` reports free disk space and fails if it drops
below 2GB. Free space by removing old exports/uploads you no longer need, or
by deleting unused models via Settings → Local Models.

## Database problems

The database is a single SQLite file at `data/meetsage.db`. If it's corrupted
or locked unexpectedly:

```bash
./scripts/stop.sh   # ensure nothing is holding a connection open
sqlite3 data/meetsage.db "PRAGMA integrity_check;"
```

Restore from backup if integrity check fails — see
[backup-recovery.md](backup-recovery.md).

## Failed jobs

Check the job's `error` field on the Jobs page — it's always populated with a
specific reason (never a bare "failed"). For a transcription/media failure,
the whole job fails (nothing downstream can proceed without a transcript). For
diarization or analysis failures, the job still completes — see
[architecture.md](architecture.md#job-processing).

**A job stuck forever in a non-`COMPLETED`/`FAILED` state that never
changes** (e.g. permanently showing `DIARIZING` with the same progress on
every refresh) is an orphan from a backend restart while that job's thread
was running — jobs run on an in-process thread pool, so killing/restarting
the backend abandons whatever was mid-flight, and nothing resumes it. This is
now handled automatically: on every backend startup, any job left in a
non-terminal state is marked `FAILED` with a clear "Interrupted by a MeetSage
restart" message (`app/workers/job_runner.py::recover_orphaned_jobs`). If you
see one that predates this fix, just restart the backend once and re-trigger
the affected step (Retry Diarization / Re-run Analysis / Retry Transcription).
