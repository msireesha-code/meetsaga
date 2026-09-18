import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.database import SessionLocal
from app.models.entities import (
    ActionItem,
    Analysis,
    Job,
    Media,
    Meeting,
    Speaker,
    Transcript,
    TranscriptSegment,
)
from app.services.analysis.base import AnalysisError
from app.services.analysis.openai_compatible import OpenAICompatibleAnalyzer
from app.services.diarization.pyannote_provider import DiarizationError, assign_speakers_to_segments, diarize
from app.services.media import MediaToolError, extract_normalized_audio, probe_media, summarize_probe
from app.services.transcription.base import TranscriptionProviderError
from app.services.transcription.registry import build_provider

logger = logging.getLogger("meetsage.jobs")

_settings = get_settings()
_executor = ThreadPoolExecutor(max_workers=max(1, _settings.max_concurrent_jobs))


_TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def submit_job(job_id: str) -> None:
    _executor.submit(_run_job, job_id)


def recover_orphaned_jobs() -> int:
    """Marks any job left in a non-terminal state as FAILED. Jobs run on an
    in-process thread pool (see _executor above) — if the backend process is
    killed or restarted while a job is running, that thread is gone and
    nothing will ever resume or complete it, leaving the DB row stuck forever
    (e.g. showing "DIARIZING" indefinitely on the Jobs page). Call this once
    at startup, before any new job can be submitted, to fail those out
    cleanly instead of leaving a permanently frozen job behind. Returns the
    number of jobs recovered."""
    db = SessionLocal()
    try:
        orphaned = db.query(Job).filter(Job.status.notin_(_TERMINAL_STATES)).all()
        for job in orphaned:
            interrupted_stage = job.stage
            job.status = "FAILED"
            job.stage = "FAILED"
            job.error = (
                f"Interrupted by a MeetSage restart while in stage '{interrupted_stage}' "
                "and was not resumed. Retry the affected step (e.g. Retry Diarization / "
                "Re-run Analysis / Retry Transcription)."
            )
            job.ended_at = _now()
        if orphaned:
            db.commit()
            logger.warning("recovered %d orphaned job(s) left over from a previous process", len(orphaned))
        return len(orphaned)
    finally:
        db.close()


def _now():
    return datetime.now(timezone.utc)


def _seconds_to_hhmmss(seconds: float) -> str:
    seconds = int(seconds)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _set_stage(db, job: Job, status: str, stage: str, progress: float | None = None):
    job.status = status
    job.stage = stage
    if progress is not None:
        job.progress = progress
    db.commit()


def _run_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("job not found", extra={"job_id": job_id})
            return
        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        media = db.query(Media).filter(Media.meeting_id == meeting.id).first()

        job.started_at = _now()
        _set_stage(db, job, "VALIDATING", "VALIDATING", 0)

        source_path = Path(media.original_path)

        # --- Media analysis ---
        _set_stage(db, job, "MEDIA_ANALYSIS", "MEDIA_ANALYSIS", 5)
        try:
            raw_probe = probe_media(source_path)
            summary = summarize_probe(raw_probe)
        except MediaToolError as exc:
            _fail(db, job, str(exc))
            return

        media.ffprobe_raw = raw_probe
        media.duration_seconds = summary["duration_seconds"]
        media.mime_type = summary["mime_type"]
        media.sample_rate = summary["sample_rate"]
        media.channels = summary["channels"]
        media.codec = summary["audio_codec"]
        meeting.duration_seconds = summary["duration_seconds"]
        db.commit()

        # --- Preprocessing: extract/normalize audio ---
        _set_stage(db, job, "PREPROCESSING", "PREPROCESSING", 15)
        normalized_path = _settings.media_dir / f"{meeting.id}.wav"
        try:
            extract_normalized_audio(source_path, normalized_path)
        except MediaToolError as exc:
            _fail(db, job, str(exc))
            return
        media.normalized_audio_path = str(normalized_path)
        db.commit()

        # --- Transcription ---
        _set_stage(db, job, "TRANSCRIBING", "TRANSCRIBING", 30)
        t0 = time.monotonic()
        last_reported = {"time": 0.0}

        def _on_transcribe_progress(fraction: float) -> None:
            now = time.monotonic()
            if now - last_reported["time"] < 2.0:
                return  # throttle DB writes; this is still real, measured progress
            last_reported["time"] = now
            job.progress = round(30 + 25 * fraction, 1)
            db.commit()

        try:
            provider = build_provider(db, job.transcription_provider, job.transcription_model)
            result = provider.transcribe(
                normalized_path,
                expected_languages=meeting.expected_languages,
                auto_detect_languages=meeting.auto_detect_languages,
                progress_callback=_on_transcribe_progress,
            )
        except TranscriptionProviderError as exc:
            _fail(db, job, f"Transcription failed: {exc}")
            return
        job.transcription_duration_seconds = time.monotonic() - t0

        transcript = Transcript(
            meeting_id=meeting.id,
            version=1,
            provider=result.provider,
            model=result.model,
            languages_detected=result.languages_detected,
            diarization_status="not_run",
        )
        db.add(transcript)
        db.flush()

        segment_rows: list[TranscriptSegment] = []
        for i, seg in enumerate(result.segments):
            row = TranscriptSegment(
                transcript_id=transcript.id,
                seq=i,
                start=seg.start,
                end=seg.end,
                language=seg.language,
                text=seg.text,
            )
            db.add(row)
            segment_rows.append(row)
        db.commit()

        # --- Diarization (independent; failure does not fail the job) ---
        if job.diarization_requested:
            _set_stage(db, job, "DIARIZING", "DIARIZING", 55)
            t0 = time.monotonic()
            transcript.diarization_status = "running"
            db.commit()
            try:
                turns = diarize(normalized_path)
                seg_dicts = [{"start": r.start, "end": r.end} for r in segment_rows]
                assign_speakers_to_segments(seg_dicts, turns)
                seen_labels = set()
                for row, d in zip(segment_rows, seg_dicts):
                    row.speaker_label = d["speaker_label"]
                    if d["speaker_label"]:
                        seen_labels.add(d["speaker_label"])
                for label in sorted(seen_labels):
                    exists = (
                        db.query(Speaker)
                        .filter(Speaker.meeting_id == meeting.id, Speaker.label == label)
                        .first()
                    )
                    if not exists:
                        db.add(Speaker(meeting_id=meeting.id, label=label))
                transcript.diarization_status = "completed"
                job.diarization_duration_seconds = time.monotonic() - t0
                db.commit()
            except DiarizationError as exc:
                logger.warning("diarization failed, continuing without speakers: %s", exc)
                transcript.diarization_status = "failed"
                job.error = (job.error + " | " if job.error else "") + f"Diarization failed: {exc}"
                db.commit()

        # --- Analysis ---
        if job.analysis_requested:
            _set_stage(db, job, "ANALYZING", "ANALYZING", 75)
            t0 = time.monotonic()
            try:
                analyzer = OpenAICompatibleAnalyzer()
                seg_dicts = [
                    {
                        "id": idx,
                        "text": row.text,
                        "speaker_label": row.speaker_label,
                        "timestamp_str": _seconds_to_hhmmss(row.start),
                        "start": row.start,
                    }
                    for idx, row in enumerate(segment_rows)
                ]
                analysis_result = analyzer.analyze(seg_dicts, job.analysis_language)

                # supersede prior analyses so history isn't destroyed
                prior_current = (
                    db.query(Analysis)
                    .filter(Analysis.meeting_id == meeting.id, Analysis.is_current.is_(True))
                    .all()
                )
                next_version = 1 + max((a.version for a in prior_current), default=0)
                for a in prior_current:
                    a.is_current = False

                analysis = Analysis(
                    meeting_id=meeting.id,
                    version=next_version,
                    provider=analysis_result.provider,
                    model=analysis_result.model,
                    language=job.analysis_language,
                    summary=analysis_result.summary,
                    key_discussion_points=analysis_result.key_discussion_points,
                    decisions=analysis_result.decisions,
                    open_issues=analysis_result.open_issues,
                    risks=analysis_result.risks,
                    important_dates=analysis_result.important_dates,
                    questions=analysis_result.questions,
                    is_current=True,
                )
                db.add(analysis)
                db.flush()

                for ai in analysis_result.action_items:
                    ts = None
                    if ai.source_segment_ids:
                        first_idx = min(ai.source_segment_ids)
                        if 0 <= first_idx < len(segment_rows):
                            ts = _seconds_to_hhmmss(segment_rows[first_idx].start)
                    db.add(
                        ActionItem(
                            analysis_id=analysis.id,
                            action=ai.action,
                            owner=ai.owner,
                            due_date=ai.due_date,
                            priority=ai.priority,
                            timestamp=ts,
                            source_segment_ids=ai.source_segment_ids,
                            context=ai.context,
                        )
                    )
                job.analysis_provider = analysis_result.provider
                job.analysis_model = analysis_result.model
                job.analysis_duration_seconds = time.monotonic() - t0
                db.commit()
            except AnalysisError as exc:
                # Analysis is independent of transcription/diarization (see spec
                # section 19): a failure here must not discard the transcript
                # (and diarization) that already completed successfully. The job
                # still finishes as COMPLETED, with the analysis error recorded;
                # the user can fix the LLM config in Settings and re-run analysis.
                logger.warning("analysis failed, continuing without analysis: %s", exc)
                job.error = (job.error + " | " if job.error else "") + f"Analysis failed: {exc}"
                db.commit()

        job.ended_at = _now()
        _set_stage(db, job, "COMPLETED", "COMPLETED", 100)
    except Exception as exc:  # noqa: BLE001
        logger.exception("unhandled job failure")
        try:
            _fail(db, job, f"Unexpected error: {exc}")
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()


def submit_reanalysis_job(job_id: str) -> None:
    _executor.submit(_run_reanalysis, job_id)


def submit_rediarization_job(job_id: str) -> None:
    _executor.submit(_run_rediarization, job_id)


def submit_retranscription_job(job_id: str) -> None:
    _executor.submit(_run_retranscription, job_id)


def _run_reanalysis(job_id: str) -> None:
    """Re-runs only the analysis stage against the latest transcript, without
    re-transcribing. Creates a new Analysis version rather than destroying prior
    results (see spec: analysis must be versionable)."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        transcript = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting.id)
            .order_by(Transcript.version.desc())
            .first()
        )
        if not transcript:
            _fail(db, job, "No transcript available to analyze")
            return

        job.started_at = _now()
        _set_stage(db, job, "ANALYZING", "ANALYZING", 20)
        t0 = time.monotonic()
        try:
            analyzer = OpenAICompatibleAnalyzer()
            seg_dicts = [
                {
                    "id": idx,
                    "text": row.text,
                    "speaker_label": row.speaker_label,
                    "timestamp_str": _seconds_to_hhmmss(row.start),
                    "start": row.start,
                }
                for idx, row in enumerate(transcript.segments)
            ]
            analysis_result = analyzer.analyze(seg_dicts, job.analysis_language)

            prior_current = (
                db.query(Analysis)
                .filter(Analysis.meeting_id == meeting.id, Analysis.is_current.is_(True))
                .all()
            )
            next_version = 1 + max((a.version for a in prior_current), default=0)
            for a in prior_current:
                a.is_current = False

            analysis = Analysis(
                meeting_id=meeting.id,
                version=next_version,
                provider=analysis_result.provider,
                model=analysis_result.model,
                language=job.analysis_language,
                summary=analysis_result.summary,
                key_discussion_points=analysis_result.key_discussion_points,
                decisions=analysis_result.decisions,
                open_issues=analysis_result.open_issues,
                risks=analysis_result.risks,
                important_dates=analysis_result.important_dates,
                questions=analysis_result.questions,
                is_current=True,
            )
            db.add(analysis)
            db.flush()
            for ai in analysis_result.action_items:
                ts = None
                if ai.source_segment_ids:
                    first_idx = min(ai.source_segment_ids)
                    if 0 <= first_idx < len(transcript.segments):
                        ts = _seconds_to_hhmmss(transcript.segments[first_idx].start)
                db.add(
                    ActionItem(
                        analysis_id=analysis.id,
                        action=ai.action,
                        owner=ai.owner,
                        due_date=ai.due_date,
                        priority=ai.priority,
                        timestamp=ts,
                        source_segment_ids=ai.source_segment_ids,
                        context=ai.context,
                    )
                )
            job.analysis_provider = analysis_result.provider
            job.analysis_model = analysis_result.model
            job.analysis_duration_seconds = time.monotonic() - t0
            job.ended_at = _now()
            _set_stage(db, job, "COMPLETED", "COMPLETED", 100)
        except AnalysisError as exc:
            _fail(db, job, f"Analysis failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("unhandled reanalysis failure")
        try:
            _fail(db, job, f"Unexpected error: {exc}")
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()


def _run_rediarization(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        media = db.query(Media).filter(Media.meeting_id == meeting.id).first()
        transcript = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting.id)
            .order_by(Transcript.version.desc())
            .first()
        )
        if not transcript or not media or not media.normalized_audio_path:
            _fail(db, job, "No processed audio available for diarization")
            return

        job.started_at = _now()
        _set_stage(db, job, "DIARIZING", "DIARIZING", 20)
        t0 = time.monotonic()
        transcript.diarization_status = "running"
        db.commit()
        try:
            turns = diarize(Path(media.normalized_audio_path))
            segment_rows = list(transcript.segments)
            seg_dicts = [{"start": r.start, "end": r.end} for r in segment_rows]
            assign_speakers_to_segments(seg_dicts, turns)
            seen_labels = set()
            for row, d in zip(segment_rows, seg_dicts):
                row.speaker_label = d["speaker_label"]
                if d["speaker_label"]:
                    seen_labels.add(d["speaker_label"])
            for label in sorted(seen_labels):
                exists = (
                    db.query(Speaker).filter(Speaker.meeting_id == meeting.id, Speaker.label == label).first()
                )
                if not exists:
                    db.add(Speaker(meeting_id=meeting.id, label=label))
            transcript.diarization_status = "completed"
            job.diarization_duration_seconds = time.monotonic() - t0
            job.ended_at = _now()
            _set_stage(db, job, "COMPLETED", "COMPLETED", 100)
        except DiarizationError as exc:
            transcript.diarization_status = "failed"
            db.commit()
            _fail(db, job, f"Diarization failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("unhandled rediarization failure")
        try:
            _fail(db, job, f"Unexpected error: {exc}")
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()


def _run_retranscription(job_id: str) -> None:
    """Re-runs only the transcription stage against the already-extracted
    normalized audio (no re-upload/re-extraction needed), creating a new
    Transcript version. Use this after a transcription fix/config change on a
    meeting that was already processed. Diarization is not carried over to the
    new version — retry it separately afterward if needed (it already targets
    the latest transcript)."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        media = db.query(Media).filter(Media.meeting_id == meeting.id).first()
        if not media or not media.normalized_audio_path:
            _fail(db, job, "No processed audio available to re-transcribe")
            return

        job.started_at = _now()
        _set_stage(db, job, "TRANSCRIBING", "TRANSCRIBING", 20)
        t0 = time.monotonic()
        last_reported = {"time": 0.0}

        def _on_progress(fraction: float) -> None:
            now = time.monotonic()
            if now - last_reported["time"] < 2.0:
                return
            last_reported["time"] = now
            job.progress = round(20 + 70 * fraction, 1)
            db.commit()

        try:
            provider = build_provider(db, job.transcription_provider, job.transcription_model)
            result = provider.transcribe(
                Path(media.normalized_audio_path),
                expected_languages=meeting.expected_languages,
                auto_detect_languages=meeting.auto_detect_languages,
                progress_callback=_on_progress,
            )
        except TranscriptionProviderError as exc:
            _fail(db, job, f"Transcription failed: {exc}")
            return
        job.transcription_duration_seconds = time.monotonic() - t0

        prior_versions = db.query(Transcript).filter(Transcript.meeting_id == meeting.id).all()
        next_version = 1 + max((t.version for t in prior_versions), default=0)

        transcript = Transcript(
            meeting_id=meeting.id,
            version=next_version,
            provider=result.provider,
            model=result.model,
            languages_detected=result.languages_detected,
            diarization_status="not_run",
        )
        db.add(transcript)
        db.flush()
        for i, seg in enumerate(result.segments):
            db.add(
                TranscriptSegment(
                    transcript_id=transcript.id,
                    seq=i,
                    start=seg.start,
                    end=seg.end,
                    language=seg.language,
                    text=seg.text,
                )
            )
        job.ended_at = _now()
        _set_stage(db, job, "COMPLETED", "COMPLETED", 100)
    except Exception as exc:  # noqa: BLE001
        logger.exception("unhandled retranscription failure")
        try:
            _fail(db, job, f"Unexpected error: {exc}")
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()


def _fail(db, job: Job, message: str) -> None:
    job.status = "FAILED"
    job.stage = "FAILED"
    job.error = message
    job.ended_at = _now()
    db.commit()
    logger.error("job failed", extra={"job_id": job.id, "error": message})
