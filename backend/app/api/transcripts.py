from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Job, Media, Meeting, Speaker, Transcript
from app.schemas import JobOut, SpeakerOut, SpeakerRenameRequest, TranscriptOut
from app.workers.job_runner import submit_rediarization_job, submit_retranscription_job

router = APIRouter(prefix="/api/meetings", tags=["transcripts"])


def _latest_transcript(db: Session, meeting_id: str) -> Transcript | None:
    return (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.version.desc())
        .first()
    )


@router.get("/{meeting_id}/transcript", response_model=TranscriptOut)
def get_transcript(meeting_id: str, db: Session = Depends(get_db)):
    transcript = _latest_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not available yet")
    return transcript


@router.get("/{meeting_id}/speakers", response_model=list[SpeakerOut])
def list_speakers(meeting_id: str, db: Session = Depends(get_db)):
    return db.query(Speaker).filter(Speaker.meeting_id == meeting_id).all()


@router.patch("/{meeting_id}/speakers/{speaker_id}", response_model=SpeakerOut)
def rename_speaker(meeting_id: str, speaker_id: str, body: SpeakerRenameRequest, db: Session = Depends(get_db)):
    speaker = db.query(Speaker).filter(Speaker.id == speaker_id, Speaker.meeting_id == meeting_id).first()
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    speaker.display_name = body.display_name
    db.commit()
    db.refresh(speaker)
    return speaker


@router.post("/{meeting_id}/rediarize", response_model=JobOut)
def rediarize(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    transcript = _latest_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript to diarize yet")

    job = Job(
        meeting_id=meeting_id,
        filename=meeting.original_filename,
        status="QUEUED",
        stage="QUEUED",
        diarization_requested=True,
        analysis_requested=False,
    )
    db.add(job)
    db.commit()
    submit_rediarization_job(job.id)
    return job


@router.post("/{meeting_id}/retranscribe", response_model=JobOut)
def retranscribe(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    media = db.query(Media).filter(Media.meeting_id == meeting_id).first()
    if not media or not media.normalized_audio_path:
        raise HTTPException(status_code=400, detail="No processed audio available to re-transcribe")

    latest = _latest_transcript(db, meeting_id)
    job = Job(
        meeting_id=meeting_id,
        filename=meeting.original_filename,
        status="QUEUED",
        stage="QUEUED",
        transcription_provider=(latest.provider if latest else None) or "local",
        transcription_model=latest.model if latest else None,
        diarization_requested=False,
        analysis_requested=False,
    )
    db.add(job)
    db.commit()
    submit_retranscription_job(job.id)
    return job
