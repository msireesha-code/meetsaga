# Build MeetSage — A Local-First Meeting Intelligence Platform

You are building **MeetSage**, a production-quality, reusable **Meeting Intelligence Platform** for Ubuntu 24.04.

### Product name

**MeetSage**

### Product description

**Meeting Intelligence Platform**

### Tagline

**Capture conversations. Understand what matters. Act on it.**

---

# 1. Vision

MeetSage should transform meeting recordings into useful, searchable and actionable information.

The core workflow is:

```text
Audio / Video
      ↓
Media Processing
      ↓
Transcription
      ↓
Speaker Diarization
      ↓
Structured Transcript
      ↓
Meeting Analysis
      ↓
Summary + Decisions + Action Items + Insights
      ↓
Review / Edit / Search / Export
```

Do NOT build MeetSage as merely a graphical wrapper around Whisper.

The architecture must allow MeetSage to evolve into a broader meeting intelligence platform.

Potential future capabilities include:

* cross-meeting search
* recurring action-item tracking
* meeting trends
* follow-up tracking
* participant insights
* project-level meeting intelligence
* integrations with Jira, Slack, email, calendar, etc.

Design the initial architecture so these capabilities can be added later without major restructuring.

---

# 2. Primary Requirements

MeetSage must:

1. Accept audio and video recordings.
2. Transcribe meetings locally by default.
3. Support configurable remote transcription providers.
4. Support English, Hindi and Telugu meetings.
5. Support code-switching between these languages.
6. Preserve the original spoken language.
7. Support speaker diarization.
8. Provide synchronized audio/video playback.
9. Generate a structured transcript.
10. Generate an executive summary.
11. Generate key discussion points.
12. Extract explicit decisions.
13. Extract structured action items.
14. Identify open issues.
15. Identify risks/concerns.
16. Extract important dates/deadlines.
17. Link analysis results back to transcript timestamps.
18. Support configurable LLM providers for analysis.
19. Provide exports.
20. Provide persistent job management.
21. Provide useful observability.
22. Provide comprehensive installation and user documentation.
23. Be maintainable and extensible.
24. Work on a CPU-only Ubuntu 24.04 system.

---

# 3. Important Environment Constraints

The target environment is:

```text
OS: Ubuntu 24.04
Hardware: CPU-only
GPU: Not required
```

FFmpeg is already available on the target environment.

The application must:

* detect the installed FFmpeg/FFprobe
* use the existing system installation where compatible
* NOT automatically replace or upgrade system FFmpeg
* document FFmpeg compatibility requirements

Do not make GPU availability a requirement.

---

# 4. UI-First Application

MeetSage must be a **web application**.

The CLI is optional and should only be provided as a supporting utility.

The primary user workflow must happen through the web UI.

Main navigation:

```text
Dashboard
New Meeting
Meetings
Jobs
Transcript
Analysis
Settings
System Status
```

The UI should be clean, modern, responsive and practical rather than visually overloaded.

---

# 5. New Meeting Workflow

The primary page should be **New Meeting**.

Example:

```text
----------------------------------------------------
New Meeting
----------------------------------------------------

Meeting Name
[ Optional meeting name ]

Upload Audio / Video
[ Drag & Drop / Browse ]

Expected Languages
☑ English
☑ Hindi
☑ Telugu

☐ Auto-detect additional languages

Transcription Provider
[ Local Model ▼ ]

Model
[ small ▼ ]

Speaker Diarization
[ Enabled ]

Generate Meeting Analysis
[ Enabled ]

Analysis Language
[ English ▼ ]

[ Start Processing ]
----------------------------------------------------
```

The transcription provider must default to the provider configured as the default provider in Settings.

The initial default MUST be:

```text
Local Model
```

---

# 6. Multilingual and Code-Switching Support — CRITICAL

This is a core requirement.

Meetings can contain:

* English
* Hindi
* Telugu

and speakers can switch between them during the same conversation or sentence.

Example:

```text
"We need to complete this by Friday.
इसके बाद हम deployment करेंगे.
ఈ పని పూర్తయ్యాక testing start చేద్దాం."
```

MeetSage MUST preserve this.

## Requirements

Do NOT:

* force the entire meeting into one language
* automatically translate the transcript
* convert Hindi/Telugu to English
* normalize multilingual speech into a single language
* discard non-English words

The transcript should reflect what was actually spoken.

Where technically supported, store language at the transcript-segment level.

Example:

```json
{
  "id": 123,
  "start": 125.42,
  "end": 131.87,
  "speaker": "SPEAKER_01",
  "language": "te",
  "text": "ఈ పని పూర్తయ్యాక testing start చేద్దాం."
}
```

---

# 7. Expected Language Configuration

Create an extensible language registry.

Initial configuration:

```python
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu"
}
```

Every new meeting should default to:

```text
☑ English
☑ Hindi
☑ Telugu
```

Also provide:

```text
☐ Auto-detect additional languages
```

The architecture must allow additional languages to be added later without redesigning the transcription system.

---

# 8. Transcript Language vs Analysis Language

These must be independent.

### Transcript

Preserve the original spoken language.

### Analysis

Allow the user to choose the output language.

Supported analysis languages initially:

```text
English
Hindi
Telugu
```

Default:

```text
Transcript: Original spoken language
Analysis: English
```

For example:

```text
Meeting:
English + Hindi + Telugu

Transcript:
English + Hindi + Telugu

Summary:
English

Action Items:
English
```

Do NOT translate the transcript unless a future translation feature is explicitly added.

---

# 9. Transcription Provider Architecture

Create a provider abstraction:

```python
class TranscriptionProvider(ABC):
    def transcribe(...)
```

Implement:

```text
LocalTranscriptionProvider
RemoteTranscriptionProvider
```

The rest of MeetSage must interact only with the provider interface.

The application must NOT contain provider-specific logic scattered throughout the codebase.

The architecture should allow future providers such as:

* faster-whisper
* OpenAI Whisper
* whisper.cpp
* remote Faster-Whisper
* OpenAI-compatible transcription APIs
* other local/remote transcription engines

---

# 10. Local Transcription

Default provider:

**Local Model**

Preferred implementation:

**faster-whisper**

provided dependency compatibility is acceptable.

Default configuration:

```text
Model: small
Device: CPU
Compute Type: int8
Threads: Auto
Maximum Concurrent Jobs: 1
```

Support:

```text
tiny
base
small
medium
large-v3
```

Do not automatically download all models.

Provide model management through Settings.

Show:

* installed models
* available models
* model size
* model status
* download option
* delete option where safe
* currently configured model

---

# 11. Audio Input

Support:

```text
.m4a
.mp3
.wav
.flac
.ogg
.aac
```

Use FFprobe for metadata.

Extract/normalize audio to a transcription-friendly format, preferably:

```text
16 kHz
Mono
PCM WAV
```

Do not modify the original recording.

---

# 12. Video Input

Support:

```text
.mp4
.mkv
.webm
.mov
.avi
```

Video processing must:

1. Preserve the original video.
2. Inspect video/audio metadata.
3. Extract audio using FFmpeg.
4. Normalize audio for transcription.
5. Transcribe the extracted audio.
6. Preserve original timestamps.
7. Allow synchronized playback with the transcript.

Never overwrite the original video.

---

# 13. Audio/Video Synchronization

For video meetings, the Transcript page must contain:

```text
Video Player
+
Timestamped Transcript
```

Clicking a transcript segment must seek the video to that timestamp.

During playback:

* determine active transcript segment
* highlight it
* automatically scroll where appropriate

For audio-only recordings provide an audio player with equivalent synchronization.

Action-item timestamps must also be clickable and navigate to the corresponding location.

---

# 14. Speaker Diarization

Speaker diarization should be enabled by default.

Prefer:

```text
pyannote.audio
```

if practical on CPU.

Example:

```text
00:02:14  SPEAKER_00
We should finish this by Friday.

00:02:19  SPEAKER_01 [Hindi]
इसके बाद deployment करेंगे.

00:02:24  SPEAKER_00 [Telugu]
ఈ పని పూర్తయ్యాక testing start చేద్దాం.
```

Allow speaker renaming:

```text
SPEAKER_00 → Ajay
SPEAKER_01 → Ravi
SPEAKER_02 → Manager
```

Store speaker names per meeting.

Diarization must be independent of transcription.

If diarization fails:

* transcript should remain available
* job should not be considered completely failed solely because diarization failed
* user should be able to retry diarization

---

# 15. Structured Transcript

The transcript must be stored as structured data.

Example:

```json
{
  "segments": [
    {
      "id": 1,
      "start": 12.42,
      "end": 17.83,
      "speaker": "SPEAKER_00",
      "language": "en",
      "text": "We need to complete this by Friday."
    },
    {
      "id": 2,
      "start": 17.84,
      "end": 23.20,
      "speaker": "SPEAKER_01",
      "language": "hi",
      "text": "इसके बाद हम deployment करेंगे."
    },
    {
      "id": 3,
      "start": 23.21,
      "end": 28.50,
      "speaker": "SPEAKER_00",
      "language": "te",
      "text": "ఈ పని పూర్తయ్యాక testing start చేద్దాం."
    }
  ]
}
```

The structured transcript is the **source of truth** for the application.

Never fabricate:

* timestamps
* speakers
* language
* transcript text
* action-item owners
* deadlines
* decisions

---

# 16. Meeting Intelligence — REQUIRED

After transcription, MeetSage must automatically generate analysis.

The analysis must include:

## Executive Summary

Concise explanation of:

* purpose of meeting
* major topics
* major outcomes

## Key Discussion Points

List the major topics discussed.

## Decisions

Only explicit decisions.

## Action Items

This is a critical feature.

Display:

| Action                      | Owner         | Due Date      | Priority | Timestamp |
| --------------------------- | ------------- | ------------- | -------- | --------- |
| Complete regression testing | Ravi          | Friday        | High     | 00:12:34  |
| Prepare deployment package  | Ajay          | Thursday      | High     | 00:18:21  |
| Share test results          | Not specified | Not specified | Medium   | 00:24:10  |

Each action item should contain:

```json
{
  "action": "Complete regression testing",
  "owner": "Ravi",
  "due_date": "Friday",
  "priority": "High",
  "timestamp": "00:12:34",
  "source_segment_ids": [123, 124],
  "context": "Regression testing needs to be completed before deployment."
}
```

Action items must retain references to their source transcript segments.

---

# 17. Action Item Accuracy

The LLM must NOT invent action-item information.

Do not hallucinate:

* owner
* due date
* priority
* commitment
* action

If owner isn't explicitly identified:

```text
Owner: Not specified
```

If due date isn't explicit:

```text
Due Date: Not specified
```

If priority isn't stated:

```text
Priority: Not specified
```

The UI should clearly distinguish information extracted from the meeting from information inferred by the AI.

Prefer conservative extraction.

---

# 18. Additional Meeting Analysis

Generate:

### Open Issues

Issues that remain unresolved.

### Risks / Concerns

Risks or concerns explicitly raised.

### Important Dates

Extract:

* deadlines
* milestones
* release dates
* planned dates

### Questions / Follow-ups

Questions that remain unanswered.

---

# 19. Analysis Architecture

Create:

```python
class MeetingAnalyzer(ABC):
    def analyze(transcript, ...)
```

Analysis must be independent of transcription.

Support OpenAI-compatible LLM endpoints.

Configuration:

```text
Provider
Base URL
API Key
Model
Temperature
Maximum Tokens
Timeout
Analysis Language
```

Possible configurations:

```text
Transcription:
Local Faster-Whisper

Analysis:
Office-hosted LLM
```

or:

```text
Transcription:
Remote Whisper

Analysis:
Local LLM
```

Do not couple Whisper configuration and LLM configuration.

---

# 20. Long Meeting Analysis

Support meetings longer than the LLM context window.

Use:

```text
Structured Transcript
        ↓
Chunking
        ↓
Chunk-level Analysis
        ↓
Hierarchical Synthesis
        ↓
Final Meeting Analysis
```

Do not simply truncate transcripts.

Ensure action items and decisions found in different chunks are preserved.

Maintain source transcript references.

---

# 21. Meeting Page

Create a central Meeting page containing:

```text
Meeting Name
Date
Duration
Status
Languages
Speakers
```

Then provide tabs:

```text
Overview
Transcript
Analysis
Action Items
Exports
```

The Overview should show:

* executive summary
* number of speakers
* languages detected
* action-item count
* decisions count
* processing information

---

# 22. Analysis Page

Provide:

```text
Meeting Analysis

Executive Summary
-----------------

Key Discussion Points
---------------------

Decisions
---------

Action Items
------------
Action | Owner | Due Date | Priority | Timestamp

Open Issues
-----------

Risks / Concerns
----------------

Important Dates
---------------

Questions / Follow-ups
----------------------
```

Every analysis item with a transcript reference should be clickable.

---

# 23. Dashboard

Display:

```text
Total Meetings
Completed
Processing
Failed
Total Meeting Duration
Action Items
Recent Meetings
```

Recent meetings:

```text
Meeting
Date
Duration
Status
Languages
Speakers
Summary
Action Items
```

---

# 24. Jobs

Use persistent SQLite job management.

States:

```text
QUEUED
VALIDATING
MEDIA_ANALYSIS
PREPROCESSING
TRANSCRIBING
DIARIZING
ANALYZING
EXPORTING
COMPLETED
FAILED
CANCELLED
```

Track:

* job ID
* meeting ID
* filename
* status
* current stage
* progress
* start time
* end time
* processing duration
* error
* transcription provider
* transcription model
* analysis provider
* analysis model

Do not fabricate percentage progress when the underlying provider does not provide it.

---

# 25. Remote Transcription

Support multiple configurable remote Whisper-compatible providers.

Example providers:

```text
Office Whisper
DGX Whisper
```

Configuration:

```text
Provider Name
Base URL
Endpoint Path
Model
API Token
Authentication Method
Connection Timeout
Read Timeout
Total Timeout
TLS Verification
```

Default endpoint:

```text
/v1/audio/transcriptions
```

Default authentication:

```text
Authorization: Bearer <TOKEN>
```

Remote calls must always happen backend-side.

Never call remote transcription APIs directly from the browser.

API tokens must:

* never be logged
* never be returned by normal API responses
* never be included in job records
* never be exposed to frontend JavaScript unnecessarily
* be masked in the UI

Provide:

```text
Test Connection
```

Optionally support:

```text
GET /v1/models
```

for model discovery.

Display a privacy warning when a remote provider is selected:

> The meeting audio will be sent to the configured remote transcription server.

For video:

> The extracted audio from the video will be sent to the configured remote transcription server.

---

# 26. Settings

Create a Settings page with:

## General

* Application name
* Storage location
* Default analysis language

## Transcription

* Default provider
* Local model
* Compute type
* CPU threads
* Maximum concurrent jobs

## Remote Transcription

* Provider management
* Base URL
* Endpoint
* Model
* API token
* TLS verification
* Timeout
* Test connection

## Languages

Default:

```text
☑ English
☑ Hindi
☑ Telugu
```

* Auto-detect additional languages

## Speaker Diarization

* enabled/disabled
* model
* CPU configuration

## LLM / Analysis

* provider
* base URL
* API key
* model
* analysis language
* temperature
* max tokens
* timeout

## Storage

* upload directory
* media directory
* transcript directory
* analysis directory
* export directory
* retention settings

## System

Display:

```text
MeetSage Version
Python Version
FFmpeg Version
FFprobe Version
CPU
RAM
Disk Space
Installed Models
```

---

# 27. Search

Implement search across:

* meeting name
* filename
* transcript
* summary
* discussion points
* decisions
* action items
* speakers
* languages

The architecture should allow full-text search to be improved later.

---

# 28. Export

Support:

```text
TXT
SRT
VTT
JSON
Markdown
```

Optionally support:

```text
PDF
```

Export:

1. Transcript
2. Meeting analysis
3. Action items

Analysis JSON:

```json
{
  "summary": "...",
  "key_discussion_points": [],
  "decisions": [],
  "action_items": [],
  "open_issues": [],
  "risks": [],
  "important_dates": [],
  "questions": []
}
```

Subtitle exports should work with the original video.

---

# 29. Observability

Use structured logging.

Every processing job must have a job ID.

Record:

```text
job_id
meeting_id
stage
provider
model
language configuration
media duration
processing duration
transcription duration
diarization duration
analysis duration
real-time factor
status
error
```

Never log:

* API tokens
* authorization headers
* full transcript by default
* sensitive request payloads

Provide useful logs for troubleshooting.

---

# 30. Security

Implement:

* extension validation
* MIME/type validation
* upload size limits
* filename sanitization
* path traversal protection
* safe subprocess execution
* no `shell=True` with user-controlled input
* secure token handling
* TLS verification enabled by default
* no secrets in logs

---

# 31. Technology Stack

Backend:

```text
Python
FastAPI
SQLite
SQLAlchemy
Pydantic
```

Frontend:

```text
React
TypeScript
Vite
```

Media:

```text
FFmpeg
FFprobe
```

Transcription:

```text
faster-whisper
```

Diarization:

```text
pyannote.audio
```

Analysis:

```text
OpenAI-compatible LLM API
```

---

# 32. Project Structure

Use a maintainable structure similar to:

```text
meetsage/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── transcription/
│   │   │   ├── media/
│   │   │   ├── diarization/
│   │   │   ├── analysis/
│   │   │   └── export/
│   │   ├── workers/
│   │   └── main.py
│   │
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   └── types/
│   └── package.json
│
├── data/
│   ├── uploads/
│   ├── media/
│   ├── transcripts/
│   ├── analysis/
│   └── exports/
│
├── scripts/
│   ├── install.sh
│   ├── start.sh
│   ├── stop.sh
│   ├── health_check.sh
│   └── download_models.sh
│
├── docs/
│   ├── installation.md
│   ├── user-guide.md
│   ├── configuration.md
│   ├── architecture.md
│   ├── troubleshooting.md
│   ├── deployment.md
│   ├── development.md
│   ├── backup-recovery.md
│   ├── faq.md
│   └── changelog.md
│
├── requirements.txt
├── README.md
└── .env.example
```

Adjust the structure if a better architecture is appropriate, but keep clear separation of concerns.

---

# 33. Comprehensive Documentation — REQUIRED

Documentation is a mandatory project deliverable.

Do not consider MeetSage complete if the software works but documentation is incomplete.

Documentation must be accurate to the actual implementation.

Do not document functionality that does not exist.

Documentation must cover both:

1. End users
2. Developers/maintainers

---

# 34. README.md

Create a comprehensive README.

Include:

### MeetSage Introduction

Explain:

* what MeetSage is
* why it exists
* core capabilities
* local-first design
* multilingual support
* meeting intelligence

### Feature List

Include:

* audio/video transcription
* English/Hindi/Telugu
* mixed-language support
* speaker diarization
* synchronized transcript
* meeting summary
* decisions
* action items
* open issues
* risks
* configurable LLM
* local/remote Whisper
* exports
* search

### Architecture

Include a clear architecture diagram.

### Requirements

Document:

* Ubuntu version
* Python version
* Node.js
* npm
* FFmpeg
* FFprobe
* CPU/RAM
* storage

### Quick Start

Provide:

```text
Install
↓
Download model
↓
Start MeetSage
↓
Open browser
↓
Upload meeting
↓
View transcript
↓
View analysis
```

Link to all detailed documentation.

---

# 35. Installation Documentation

Create:

```text
docs/installation.md
```

Provide a complete Ubuntu 24.04 installation guide.

Include:

## System Requirements

Explain minimum and recommended hardware.

## Verify Environment

Commands such as:

```bash
lsb_release -a
python3 --version
node --version
npm --version
ffmpeg -version
ffprobe -version
```

## Install Dependencies

Provide exact commands.

## Python Virtual Environment

Explain creation and activation.

## Backend Installation

Provide exact commands.

## Frontend Installation

Provide exact commands.

## Model Installation

Explain available models and how to download them.

## First Startup

Explain:

```bash
./scripts/start.sh
```

## Health Check

Explain:

```bash
./scripts/health_check.sh
```

## Accessing the UI

Explain how to determine the URL and port.

---

# 36. User Guide

Create:

```text
docs/user-guide.md
```

Provide step-by-step instructions for:

### Starting MeetSage

### Dashboard

Explain each dashboard section.

### Creating a Meeting

Explain every field.

### Uploading Audio

### Uploading Video

### Selecting Languages

Explain the English/Hindi/Telugu defaults.

### Mixed-Language Meetings

Explain code-switching behavior.

### Selecting Transcription Provider

Explain local vs remote.

### Speaker Diarization

Explain speaker labels and renaming.

### Monitoring Processing

Explain all job stages.

### Viewing Transcript

Explain:

* timestamps
* speakers
* languages
* search
* editing
* synchronization

### Viewing Analysis

Explain:

* summary
* discussion points
* decisions
* action items
* open issues
* risks
* dates
* questions

### Reviewing Action Items

Explain why AI-generated action items should be verified against the transcript.

### Exporting

Explain every supported export format.

---

# 37. Configuration Documentation

Create:

```text
docs/configuration.md
```

Document every configuration setting.

Include examples for:

### Local transcription

```text
Provider: Local Model
Model: small
Device: CPU
Compute Type: int8
```

### Remote transcription

Use placeholders:

```text
Provider: Office Whisper
Base URL: https://whisper.example.internal
Endpoint: /v1/audio/transcriptions
Model: whisper-large-v3
TLS Verification: Enabled
```

Never include real credentials.

### LLM

Document OpenAI-compatible configuration.

### Environment Variables

Document every `.env` variable.

Maintain:

```text
.env.example
```

Never commit real secrets.

---

# 38. Troubleshooting Guide

Create:

```text
docs/troubleshooting.md
```

Include troubleshooting for:

* MeetSage won't start
* backend unavailable
* frontend unavailable
* FFmpeg missing
* FFprobe missing
* model download failure
* slow transcription
* high CPU usage
* memory exhaustion
* poor Hindi transcription
* poor Telugu transcription
* mixed-language transcription problems
* diarization failure
* remote Whisper connection failure
* authentication failure
* TLS failure
* LLM failure
* context-length failure
* video processing failure
* insufficient disk space
* database problems
* failed jobs

Provide concrete commands for diagnosis.

---

# 39. Architecture Documentation

Create:

```text
docs/architecture.md
```

Document:

* frontend architecture
* backend architecture
* API architecture
* database model
* filesystem storage
* job processing
* provider abstraction
* transcription pipeline
* diarization
* analysis
* export
* error handling

Include diagrams where useful.

---

# 40. Developer Documentation

Create:

```text
docs/development.md
```

Document:

* repository structure
* development setup
* backend development
* frontend development
* testing
* linting
* formatting
* debugging
* database migrations
* adding providers
* adding languages
* adding analysis modules
* adding export formats
* adding API endpoints

Include an example showing how to add a new transcription provider.

---

# 41. Deployment Documentation

Create:

```text
docs/deployment.md
```

Document:

* local deployment
* production-style deployment
* systemd option
* ports
* filesystem permissions
* logs
* environment configuration
* service management
* backup considerations

---

# 42. Backup and Recovery

Create:

```text
docs/backup-recovery.md
```

Document:

### What to back up

```text
SQLite database
meeting media
transcripts
analysis
exports
configuration
```

Explain:

* backup procedure
* restore procedure
* migration to another Ubuntu machine
* relationship between database and filesystem data

---

# 43. FAQ

Create:

```text
docs/faq.md
```

Answer:

* Is MeetSage local?
* Does audio leave my computer?
* When is remote transcription used?
* Can it work offline?
* Can it handle Hindi?
* Can it handle Telugu?
* Can one meeting use multiple languages?
* Does it translate?
* Can it process video?
* Can speakers be renamed?
* How are action items generated?
* Can action items be wrong?
* Can I use my own Whisper server?
* Can I use a local LLM?
* Where are recordings stored?
* Where are transcripts stored?
* How do I change models?
* How do I update MeetSage?

---

# 44. Backup and Upgrade Safety

The application must never silently delete user meeting data.

Document an upgrade procedure:

```text
Backup
↓
Stop MeetSage
↓
Update source
↓
Update dependencies
↓
Run migrations
↓
Verify configuration
↓
Start MeetSage
↓
Run health check
```

---

# 45. Installation Scripts

Provide:

```text
scripts/install.sh
scripts/start.sh
scripts/stop.sh
scripts/health_check.sh
scripts/download_models.sh
```

`install.sh` should:

1. Check Ubuntu compatibility.
2. Check Python.
3. Check Node/npm.
4. Check FFmpeg.
5. Create Python venv.
6. Install backend dependencies.
7. Install frontend dependencies.
8. Create directories.
9. Initialize database.
10. Create `.env` if appropriate.
11. Validate installation.
12. Print next steps.

It must NOT:

* replace FFmpeg
* silently download huge models
* overwrite user data
* expose secrets

---

# 46. Health Check

`health_check.sh` must verify:

```text
Backend
Database
Storage
FFmpeg
FFprobe
Configuration
Installed models
Disk space
```

Output should clearly indicate:

```text
PASS
WARN
FAIL
```

---

# 47. Testing

Create automated tests for:

## Media

* audio upload
* video upload
* metadata
* audio extraction
* invalid formats
* corrupted media

## Transcription

* local transcription
* remote transcription
* provider switching
* English
* Hindi
* Telugu
* English + Hindi
* English + Telugu
* Hindi + Telugu
* English + Hindi + Telugu
* code-switching
* segment language

## Diarization

* multiple speakers
* speaker renaming
* diarization failure
* retry

## Analysis

* summary
* discussion points
* decisions
* action items
* missing owner
* missing deadline
* missing priority
* source timestamps
* long transcripts
* LLM failures

## UI

* upload
* processing
* transcript
* video synchronization
* action-item navigation
* speaker editing
* exports
* settings

## Recovery

* restart
* remote failure
* LLM failure
* diarization failure
* FFmpeg failure
* disk issues

Use mocks for external services where appropriate.

---

# 48. Security Testing

Test:

* invalid uploads
* oversized files
* malicious filenames
* path traversal
* command injection attempts
* malformed provider URLs
* invalid authentication
* secret leakage in logs
* unauthorized access to stored media

---

# 49. Development Process

Before implementing:

1. Inspect the existing repository.
2. Understand current code and structure.
3. Check Python version.
4. Check Node/npm.
5. Check FFmpeg/FFprobe.
6. Check CPU/RAM/disk.
7. Validate dependency compatibility.
8. Create an implementation plan.

Then implement in logical phases.

After each phase:

* run tests
* run the application
* perform smoke tests
* fix issues
* update documentation

Do NOT implement everything first and test only at the end.

---

# 50. Recommended Implementation Phases

Use approximately this sequence:

### Phase 1 — Foundation

* repository structure
* FastAPI
* React
* SQLite
* configuration
* basic UI
* health check

### Phase 2 — Media

* upload
* FFprobe
* audio extraction
* video processing

### Phase 3 — Local Transcription

* provider abstraction
* faster-whisper
* model management
* jobs

### Phase 4 — Multilingual Support

* English
* Hindi
* Telugu
* language configuration
* code-switching
* segment language

### Phase 5 — Diarization

* pyannote
* speaker mapping
* retry

### Phase 6 — Transcript UI

* player
* synchronized transcript
* search
* speaker editing

### Phase 7 — Meeting Intelligence

* LLM provider
* summary
* discussion points
* decisions
* action items
* open issues
* risks
* dates

### Phase 8 — Remote Providers

* remote Whisper
* provider management
* connection testing
* authentication
* retries

### Phase 9 — Export/Search

* TXT
* SRT
* VTT
* JSON
* Markdown
* search

### Phase 10 — Documentation & Production Readiness

* complete documentation
* installation scripts
* health check
* backup/recovery
* troubleshooting
* final tests

---

# 51. Performance

Optimize for CPU-only execution.

Consider:

* faster-whisper
* int8 computation
* configurable CPU threads
* single-job default concurrency
* efficient audio preprocessing
* avoiding unnecessary media conversions
* streaming/chunked processing where practical
* persistent job state

Show useful performance information such as:

```text
Media duration: 18m 05s
Processing time: 7m 32s
Real-time factor: 0.42
```

Do not fabricate performance measurements.

---

# 52. Data Model

Design database entities around:

```text
Meeting
Job
Media
Transcript
TranscriptSegment
Speaker
Analysis
ActionItem
Provider
Settings
```

Action items should maintain relationships to transcript segments.

Analysis should be versionable so that re-running analysis does not destroy previous results unexpectedly.

Consider storing:

```text
analysis_version
analysis_provider
analysis_model
analysis_timestamp
```

---

# 53. Reprocessing

Allow users to re-run independently where practical:

```text
Transcription
Diarization
Analysis
```

For example:

* change LLM → re-run analysis without retranscribing
* change diarization → re-run diarization without retranscribing
* change transcription model → create a new transcription version

Do not unnecessarily repeat expensive processing.

---

# 54. Error Handling

Errors must be:

* captured
* associated with the job
* shown clearly in UI
* logged with job ID
* classified where possible

Example:

```text
Transcription failed
Reason: Remote server returned HTTP 503
Provider: Office Whisper
Model: whisper-large-v3
Retry: Available
```

Do not expose secrets in errors.

---

# 55. Privacy Model

MeetSage should be **local-first**.

When using local transcription:

```text
Recording
    ↓
User's Machine
    ↓
Local Whisper
    ↓
Local Transcript
    ↓
Configured LLM
```

If the LLM is remote, clearly communicate that transcript data may leave the machine.

When remote transcription is selected:

```text
Recording
    ↓
MeetSage Backend
    ↓
Remote Whisper Server
```

Clearly communicate this to users.

---

# 56. Final UI Acceptance Test

A fresh user must be able to:

1. Start MeetSage.
2. Open the web UI.
3. Upload an `.m4a`.
4. Upload an `.mp4`.
5. See English/Hindi/Telugu selected by default.
6. Select Local Model.
7. Start processing.
8. Monitor the job.
9. View the transcript.
10. See speaker labels.
11. Rename speakers.
12. Play the media.
13. Click transcript timestamps.
14. See transcript synchronization.
15. Process a mixed English/Hindi/Telugu meeting.
16. Generate an English summary.
17. See key discussion points.
18. See decisions.
19. See action items.
20. See owner and due date when explicitly stated.
21. See "Not specified" when unavailable.
22. Click action items to navigate to source timestamps.
23. Export transcript.
24. Export analysis.
25. Configure remote Whisper.
26. Test remote Whisper connection.
27. Configure an independent LLM.
28. Re-run analysis.
29. Restart MeetSage.
30. Confirm completed meetings remain available.
31. Run health check.
32. Follow the installation documentation.
33. Follow the user guide.
34. Follow troubleshooting documentation for a simulated failure.

---

# 57. Final Design Principle

MeetSage is NOT:

```text
"Whisper with a web UI"
```

MeetSage IS:

```text
              ┌───────────────────┐
              │   Audio / Video   │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Media Processing  │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │  Transcription    │
              │ Local / Remote    │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Speaker           │
              │ Diarization       │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Structured        │
              │ Transcript        │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Meeting           │
              │ Intelligence      │
              └─────────┬─────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
      Summary       Decisions    Action Items
          │             │             │
          └─────────────┼─────────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Search / Review   │
              │ Export / Insights │
              └───────────────────┘
```

The **structured transcript is the source of truth**.

All derived intelligence must retain references back to the source transcript wherever practical.

The application must be:

* local-first
* multilingual
* provider-independent
* CPU-friendly
* secure
* observable
* testable
* documented
* maintainable
* extensible

Most importantly, build MeetSage as a **real reusable application**, not a proof-of-concept or one-off script.

At the end of implementation, provide a concise final report containing:

1. What was implemented.
2. Project structure.
3. How to install.
4. How to start.
5. How to configure local transcription.
6. How to configure remote transcription.
7. How to configure LLM analysis.
8. How to download models.
9. How to run tests.
10. Where the documentation is located.
11. Known limitations.
12. Recommended future enhancements.

Do not claim a feature is complete unless it has actually been implemented and tested.

