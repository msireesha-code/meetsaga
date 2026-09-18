# FAQ

**Is MeetSage local?**
By default, yes. Local transcription (faster-whisper) and diarization
(pyannote.audio) run entirely on your machine. Only the analysis stage talks
to an external service, and only because you configure an LLM — if that LLM
is a local server, nothing leaves your machine at all.

**Does audio leave my computer?**
Only if you explicitly select a remote transcription provider (Settings →
Remote Transcription Providers), and only the extracted/normalized audio for
that one meeting — never the original file, never anything from other
meetings. The UI shows an explicit warning before you process a meeting with a
remote provider selected.

**When is remote transcription used?**
Only when you pick a configured remote provider instead of "Local Model" for
a specific meeting (or set one as the site default in Settings). It's never
automatic or silent.

**Can it work offline?**
Local transcription and diarization: yes, once the Whisper model and
pyannote models are already downloaded. Analysis: only if your configured LLM
is also local/offline (e.g. a local Ollama/vLLM server) — the default
configuration points at the real OpenAI API, which needs internet.

**Can it handle Hindi?**
Yes — Hindi is one of the three default expected languages, transcribed
directly (not translated).

**Can it handle Telugu?**
Yes, same as above.

**Can one meeting use multiple languages?**
Yes — this is a core design goal, including code-switching mid-sentence. The
transcript is never forced into a single language. See
[architecture.md](architecture.md#multilingual-transcription) for how
per-segment language tagging actually works and its limits.

**Does it translate?**
No. The transcript always preserves the original spoken language(s) exactly.
Only the *analysis* (summary, action items, etc.) is generated in your chosen
analysis language, independently of the transcript's language.

**Can it process video?**
Yes (`.mp4 .mkv .webm .mov .avi`). Audio is extracted for transcription; the
original video is never modified and is what plays back in the Transcript
tab, synchronized with the transcript.

**Can speakers be renamed?**
Yes, from the Transcript tab. Renames apply consistently across the
transcript view and all export formats.

**How are action items generated?**
By an LLM reading the transcript, instructed to extract only what was
explicitly said — never to invent an owner, due date, or priority. Missing
fields show as "Not specified" rather than a guess. See
[user-guide.md](user-guide.md#reviewing-action-items).

**Can action items be wrong?**
Yes — always verify against the source transcript (click the timestamp) before
treating an action item as a firm commitment. The conservative extraction
policy reduces invented details, but the LLM can still misread ambiguous or
subtle statements.

**Can I use my own Whisper server?**
Yes — any server exposing an OpenAI-compatible
`/v1/audio/transcriptions` endpoint. Configure it under Settings → Remote
Transcription Providers.

**Can I use a local LLM?**
Yes — any OpenAI-compatible chat completions endpoint (Ollama, LM Studio,
vLLM with a compatible shim, etc.). Set `LLM_BASE_URL` (and `LLM_MODEL`) in
`.env`; `LLM_API_KEY` can be left as a placeholder for a server that doesn't
require one.

**Where are recordings stored?**
`data/uploads/` (originals, untouched) and `data/media/` (extracted/
normalized audio for transcription). See
[configuration.md](configuration.md#storage-layout).

**Where are transcripts stored?**
In the SQLite database (`data/meetsage.db`), not as separate files — see
[backup-recovery.md](backup-recovery.md).

**How do I change models?**
Settings → Local Models (download/delete/select), or per-meeting in New
Meeting. Changing the default model doesn't retroactively re-transcribe past
meetings.

**How do I update MeetSage?**
See [backup-recovery.md](backup-recovery.md#upgrade-procedure) — back up
first, there's no schema migration framework yet, so review that section's
caveat before pulling a new version.
