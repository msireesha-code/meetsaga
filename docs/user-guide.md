# User Guide

## Starting MeetSage

```bash
./scripts/start.sh
```

Open http://localhost:5173. The left navigation has: Dashboard, New Meeting,
Meetings, Jobs, Search, Settings, System Status.

## Dashboard

Shows: total meetings, completed/processing/failed counts (based on each
meeting's most recent job), total recorded meeting duration, total action
items across all meetings, and a table of recent meetings.

## Creating a Meeting

Go to **New Meeting**. Fields:

- **Meeting Name** — optional; defaults to the uploaded filename if left blank.
- **Upload Audio/Video** — drag-and-drop or click to browse. Supported:
  `.m4a .mp3 .wav .flac .ogg .aac` (audio), `.mp4 .mkv .webm .mov .avi` (video).
- **Expected Languages** — checkboxes for English/Hindi/Telugu, all checked by
  default. This tells the transcription model which languages to expect; it
  does not restrict the actual transcript content (see
  [Mixed-Language Meetings](#mixed-language-meetings)).
- **Auto-detect additional languages** — unchecked by default; enables
  multilingual detection even for languages outside the checked set.
- **Transcription Provider** — "Local Model" (default) or any remote provider
  you've configured in Settings.
- **Model** — which local Whisper model to use (only shown for Local Model).
- **Speaker Diarization** — on by default.
- **Generate Meeting Analysis** — on by default; requires an LLM configured in
  Settings, or the analysis stage will fail gracefully (transcript/diarization
  still complete — see [Reviewing Action Items](#reviewing-action-items)).
- **Analysis Language** — the language the summary/action items are written in
  (independent of the transcript's language).

Click **Start Processing**. You're redirected to the meeting's page, where a
processing banner shows the current stage.

## Uploading Audio / Video

The file is validated (extension, size limit) and stored under `data/uploads/`
with a generated internal filename — your original filename is preserved only
as display metadata, never used as a filesystem path (this prevents path
traversal from a malicious filename). The original file is never modified.

For video, MeetSage extracts and normalizes the audio (16kHz mono PCM WAV)
for transcription into `data/media/`, while the original video is left
untouched and is what the video player in the Transcript tab actually plays.

## Selecting Languages

The default set is English + Hindi + Telugu. Uncheck any you don't expect to
reduce (very slightly) the transcription model's search space. This is a hint,
not a hard filter — if the meeting contains a fourth language and
"auto-detect additional languages" is checked, it will still be transcribed
and tagged.

## Mixed-Language Meetings

MeetSage never translates, merges, or forces a meeting into one language. The
transcript preserves exactly what was said, including sentences that switch
between English/Hindi/Telugu mid-thought. Each transcript segment carries a
`language` tag — see
[Architecture: Multilingual Transcription](architecture.md#multilingual-transcription)
for exactly how that tag is derived and its limits with code-switching within
a single segment.

## Selecting Transcription Provider

- **Local Model**: runs on your machine via faster-whisper. Default and
  recommended for privacy — nothing leaves your machine at this stage.
- **Remote provider**: sends the extracted/normalized audio to a configured
  HTTP endpoint (see [Configuration](configuration.md#remote-transcription)).
  The UI shows an explicit privacy warning when a remote provider is selected:
  *"The meeting audio will be sent to the configured remote transcription
  server."* All remote calls happen backend-side — the browser never talks to
  the remote provider directly, and its API token is never sent to or
  displayed in the browser.

## Speaker Diarization

Runs independently of transcription. If it fails (e.g. missing HuggingFace
access), the transcript is still fully available — you'll see the error on the
Jobs page and can retry diarization alone from the meeting's Analysis tab
("Retry Diarization") without re-transcribing.

Speakers show up as `SPEAKER_00`, `SPEAKER_01`, etc. Rename them from the
Transcript tab — renames apply everywhere: the transcript view, exports, and
(going forward) any new analysis.

## Monitoring Processing

The **Jobs** page lists every job with its status
(`QUEUED → VALIDATING → MEDIA_ANALYSIS → PREPROCESSING → TRANSCRIBING →
DIARIZING → ANALYZING → COMPLETED`, or `FAILED`/`CANCELLED`), current stage,
and (during transcription) a real progress percentage based on how much audio
has actually been processed — not a fabricated estimate. Errors from any
stage are shown directly on this page.

A queued job can be cancelled; a running job cannot be safely interrupted
mid-stage and will run to completion or failure.

## Viewing Transcript

Open a meeting → **Transcript** tab. Shows:

- **Timestamps** — start time of each segment.
- **Speakers** — renamed labels if set.
- **Languages** — a small tag per segment (`en`/`hi`/`te`).
- **Synchronization** — click any segment to seek the audio/video player to
  that moment; the currently-playing segment is highlighted and auto-scrolled
  into view.
- **Speaker renaming** — from the panel next to the player.

There is no inline transcript text editing in this version — the transcript is
treated as the authoritative record of what the model produced.

## Viewing Analysis

Open a meeting → **Analysis** tab: executive summary, key discussion points,
decisions, action items (table), open issues, risks/concerns, important
dates, and questions/follow-ups. Every item with transcript references is
clickable and jumps you to the Transcript tab at that moment.

**Re-run Analysis** creates a new analysis version (previous versions are kept,
not deleted) — useful after changing your LLM configuration or the analysis
language.

## Reviewing Action Items

**Action items are extracted conservatively, not guessed.** If a meeting
didn't explicitly name an owner, due date, or priority, the field shows
**"Not specified"** rather than a plausible-looking invention. Always
cross-check action items against the source transcript (click the timestamp)
before treating them as commitments — the LLM can still misread a subtle
statement, and "Not specified" fields mean *you* need to fill the gap.

## Exporting

From the **Exports** tab: download the transcript as TXT, SRT, VTT, JSON, or
Markdown, and the analysis as JSON or Markdown. Subtitle exports (SRT/VTT) use
the same timestamps as the original recording, so they line up if you use them
with the original video file in another player.
