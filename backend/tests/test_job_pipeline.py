"""Tests the job orchestration logic in app.workers.job_runner: stage transitions,
and the fault-tolerance guarantees from the spec that this project's real usage
already exercised — diarization and analysis failures must not discard a
transcript that already completed successfully.

Media probing/extraction use the real ffmpeg/ffprobe (fast and deterministic for
a 1-2s synthetic clip). The transcription provider, diarizer, and LLM analyzer
are mocked so tests are fast and don't depend on downloaded models or a live LLM.
"""
import subprocess
from types import SimpleNamespace

import app.workers.job_runner as job_runner
from app.models.entities import Analysis, Job, Media, Meeting, Speaker, Transcript
from app.services.analysis.base import ActionItemResult, AnalysisError, AnalysisResult
from app.services.diarization.pyannote_provider import DiarizationError, SpeakerTurn
from app.services.transcription.base import TranscriptionResult, TranscriptSegmentResult


def _make_meeting_and_job(db, tmp_path, *, diarization_requested=True, analysis_requested=True):
    wav_path = tmp_path / "input.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-ar", "16000", "-ac", "1", str(wav_path)],
        capture_output=True,
        check=True,
    )

    meeting = Meeting(name="Test Meeting", original_filename="input.wav", media_type="audio", expected_languages=["en"])
    db.add(meeting)
    db.flush()
    media = Media(meeting_id=meeting.id, original_path=str(wav_path))
    db.add(media)
    job = Job(
        meeting_id=meeting.id,
        filename="input.wav",
        status="QUEUED",
        stage="QUEUED",
        transcription_provider="local",
        transcription_model="tiny",
        diarization_requested=diarization_requested,
        analysis_requested=analysis_requested,
        analysis_language="en",
    )
    db.add(job)
    db.commit()
    return meeting, job


def _fake_transcription_provider(text="We must ship by Friday."):
    return SimpleNamespace(
        transcribe=lambda *a, **k: TranscriptionResult(
            segments=[TranscriptSegmentResult(start=0.0, end=1.0, text=text, language="en")],
            languages_detected=["en"],
            provider="local",
            model="tiny",
        )
    )


def test_diarization_failure_keeps_job_completed_and_transcript_intact(db_session, tmp_path, monkeypatch):
    meeting, job = _make_meeting_and_job(db_session, tmp_path, diarization_requested=True, analysis_requested=False)

    monkeypatch.setattr(job_runner, "build_provider", lambda db, provider, model: _fake_transcription_provider())

    def _boom(audio_path):
        raise DiarizationError("no HF access to gated repo")

    monkeypatch.setattr(job_runner, "diarize", _boom)

    job_runner._run_job(job.id)
    db_session.expire_all()

    updated = db_session.query(Job).filter(Job.id == job.id).first()
    assert updated.status == "COMPLETED"  # per spec: diarization failure must not fail the job
    assert "Diarization failed" in updated.error

    transcript = db_session.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
    assert transcript is not None
    assert transcript.diarization_status == "failed"
    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "We must ship by Friday."


def test_analysis_failure_keeps_job_completed_and_transcript_intact(db_session, tmp_path, monkeypatch):
    meeting, job = _make_meeting_and_job(db_session, tmp_path, diarization_requested=False, analysis_requested=True)

    monkeypatch.setattr(job_runner, "build_provider", lambda db, provider, model: _fake_transcription_provider())

    class FakeAnalyzer:
        def __init__(self, *a, **k):
            pass

        def analyze(self, *a, **k):
            raise AnalysisError("No LLM API key configured")

    monkeypatch.setattr(job_runner, "OpenAICompatibleAnalyzer", FakeAnalyzer)

    job_runner._run_job(job.id)
    db_session.expire_all()

    updated = db_session.query(Job).filter(Job.id == job.id).first()
    assert updated.status == "COMPLETED"  # analysis is independent; must not discard the transcript
    assert "Analysis failed" in updated.error

    transcript = db_session.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
    assert transcript is not None
    assert len(transcript.segments) == 1

    analysis = db_session.query(Analysis).filter(Analysis.meeting_id == meeting.id).first()
    assert analysis is None


def test_successful_pipeline_creates_expected_records(db_session, tmp_path, monkeypatch):
    meeting, job = _make_meeting_and_job(db_session, tmp_path, diarization_requested=True, analysis_requested=True)

    monkeypatch.setattr(job_runner, "build_provider", lambda db, provider, model: _fake_transcription_provider())
    monkeypatch.setattr(
        job_runner, "diarize", lambda audio_path: [SpeakerTurn(start=0.0, end=1.0, speaker="SPEAKER_00")]
    )

    class FakeAnalyzer:
        def __init__(self, *a, **k):
            pass

        def analyze(self, segments, language):
            return AnalysisResult(
                summary="Ship by Friday.",
                action_items=[
                    ActionItemResult(
                        action="Ship it",
                        owner="Not specified",
                        due_date="Friday",
                        priority="Not specified",
                        source_segment_ids=[0],
                    )
                ],
                provider="test",
                model="test-model",
            )

    monkeypatch.setattr(job_runner, "OpenAICompatibleAnalyzer", FakeAnalyzer)

    job_runner._run_job(job.id)
    db_session.expire_all()

    updated = db_session.query(Job).filter(Job.id == job.id).first()
    assert updated.status == "COMPLETED"
    assert updated.error is None

    transcript = db_session.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
    assert transcript.diarization_status == "completed"
    assert transcript.segments[0].speaker_label == "SPEAKER_00"

    speakers = db_session.query(Speaker).filter(Speaker.meeting_id == meeting.id).all()
    assert any(s.label == "SPEAKER_00" for s in speakers)

    analysis = (
        db_session.query(Analysis)
        .filter(Analysis.meeting_id == meeting.id, Analysis.is_current.is_(True))
        .first()
    )
    assert analysis is not None
    assert analysis.action_items[0].owner == "Not specified"
    assert analysis.action_items[0].due_date == "Friday"
    assert analysis.action_items[0].timestamp == "00:00:00"  # derived from source segment start, never fabricated


def test_retranscription_creates_new_transcript_version_without_touching_old_one(db_session, tmp_path, monkeypatch):
    from app.models.entities import Media as MediaModel

    meeting, job = _make_meeting_and_job(db_session, tmp_path, diarization_requested=False, analysis_requested=False)

    media = db_session.query(MediaModel).filter(MediaModel.meeting_id == meeting.id).first()
    media.normalized_audio_path = str(tmp_path / "input.wav")  # reuse the same synthetic file as "normalized" audio
    db_session.commit()

    monkeypatch.setattr(
        job_runner, "build_provider", lambda db, provider, model: _fake_transcription_provider("First pass text.")
    )
    job_runner._run_job(job.id)
    db_session.expire_all()

    old_transcript = (
        db_session.query(Transcript).filter(Transcript.meeting_id == meeting.id).order_by(Transcript.version).first()
    )
    assert old_transcript.version == 1
    assert old_transcript.segments[0].text == "First pass text."

    retranscribe_job = Job(
        meeting_id=meeting.id,
        filename="input.wav",
        status="QUEUED",
        stage="QUEUED",
    )
    db_session.add(retranscribe_job)
    db_session.commit()

    monkeypatch.setattr(
        job_runner, "build_provider", lambda db, provider, model: _fake_transcription_provider("Corrected full text.")
    )
    job_runner._run_retranscription(retranscribe_job.id)
    db_session.expire_all()

    updated = db_session.query(Job).filter(Job.id == retranscribe_job.id).first()
    assert updated.status == "COMPLETED"

    all_transcripts = (
        db_session.query(Transcript).filter(Transcript.meeting_id == meeting.id).order_by(Transcript.version).all()
    )
    assert [t.version for t in all_transcripts] == [1, 2]
    assert all_transcripts[0].segments[0].text == "First pass text."  # untouched
    assert all_transcripts[1].segments[0].text == "Corrected full text."  # the new version


def test_recover_orphaned_jobs_fails_stuck_jobs_left_by_a_dead_process(db_session):
    """Regression test for a real bug found on 2026-09-09: a job left
    DIARIZING when the backend process that owned its thread was restarted
    stayed stuck in that state forever, since nothing else was ever going to
    resume it."""
    meeting = Meeting(name="Orphan Test", original_filename="f.wav", media_type="audio", expected_languages=["en"])
    db_session.add(meeting)
    db_session.flush()
    stuck_job = Job(meeting_id=meeting.id, filename="f.wav", status="DIARIZING", stage="DIARIZING")
    completed_job = Job(meeting_id=meeting.id, filename="f.wav", status="COMPLETED", stage="COMPLETED")
    db_session.add_all([stuck_job, completed_job])
    db_session.commit()

    recovered_count = job_runner.recover_orphaned_jobs()
    db_session.expire_all()

    assert recovered_count >= 1
    updated_stuck = db_session.query(Job).filter(Job.id == stuck_job.id).first()
    assert updated_stuck.status == "FAILED"
    assert "Interrupted by a MeetSage restart" in updated_stuck.error
    assert "DIARIZING" in updated_stuck.error

    # A job that had already finished must be left completely alone.
    untouched_completed = db_session.query(Job).filter(Job.id == completed_job.id).first()
    assert untouched_completed.status == "COMPLETED"
    assert untouched_completed.error is None
