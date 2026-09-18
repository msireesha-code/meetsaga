import json
import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.entities import Media, Meeting
from app.schemas import MeetingCreateResponse, MeetingOut
from app.services.media import UploadValidationError, classify_media_type, sanitize_filename, validate_size
from app.workers.job_runner import submit_job
from app.models.entities import Job

logger = logging.getLogger("meetsage.api.meetings")
router = APIRouter(prefix="/api/meetings", tags=["meetings"])
settings = get_settings()


@router.post("", response_model=MeetingCreateResponse)
async def create_meeting(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    expected_languages: str = Form('["en","hi","te"]'),
    auto_detect_languages: bool = Form(False),
    transcription_provider: str = Form("local"),
    transcription_model: str | None = Form(None),
    diarization_enabled: bool = Form(True),
    generate_analysis: bool = Form(True),
    analysis_language: str = Form("en"),
    db: Session = Depends(get_db),
):
    try:
        safe_name = sanitize_filename(file.filename or "upload")
        media_type = classify_media_type(safe_name)
        languages = json.loads(expected_languages)
        if not isinstance(languages, list) or not languages:
            raise UploadValidationError("expected_languages must be a non-empty list")
    except (UploadValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meeting = Meeting(
        name=name or safe_name,
        original_filename=safe_name,
        media_type=media_type,
        expected_languages=languages,
        auto_detect_languages=auto_detect_languages,
    )
    db.add(meeting)
    db.flush()

    stored_name = f"{meeting.id}_{uuid.uuid4().hex[:8]}{Path(safe_name).suffix.lower()}"
    dest_path = settings.uploads_dir / stored_name

    size = 0
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    try:
        with open(dest_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    out.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_size_mb}MB limit")
                out.write(chunk)
        validate_size(size, settings.max_upload_size_mb)
    except UploadValidationError as exc:
        dest_path.unlink(missing_ok=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media = Media(meeting_id=meeting.id, original_path=str(dest_path))
    db.add(media)

    job = Job(
        meeting_id=meeting.id,
        filename=safe_name,
        status="QUEUED",
        stage="QUEUED",
        transcription_provider=transcription_provider,
        transcription_model=transcription_model,
        diarization_requested=diarization_enabled,
        analysis_requested=generate_analysis,
        analysis_language=analysis_language,
    )
    db.add(job)
    db.commit()

    submit_job(job.id)
    return MeetingCreateResponse(meeting_id=meeting.id, job_id=job.id)


@router.get("", response_model=list[MeetingOut])
def list_meetings(db: Session = Depends(get_db), q: str | None = None, limit: int = 50, offset: int = 0):
    query = db.query(Meeting)
    if q:
        like = f"%{q}%"
        query = query.filter(Meeting.name.ilike(like))
    return query.order_by(Meeting.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/{meeting_id}/job", response_model=dict)
def get_latest_job(meeting_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.meeting_id == meeting_id).order_by(Job.created_at.desc()).first()
    if not job:
        raise HTTPException(status_code=404, detail="No job found for meeting")
    from app.schemas import JobOut

    return JobOut.model_validate(job).model_dump()


@router.get("/{meeting_id}/media")
def stream_media(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.media:
        raise HTTPException(status_code=404, detail="Media not found")
    path = Path(meeting.media.original_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing from storage")
    return FileResponse(path, filename=meeting.original_filename)


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.media and meeting.media.original_path:
        Path(meeting.media.original_path).unlink(missing_ok=True)
    if meeting.media and meeting.media.normalized_audio_path:
        Path(meeting.media.normalized_audio_path).unlink(missing_ok=True)
    db.delete(meeting)
    db.commit()
    return {"deleted": True}
