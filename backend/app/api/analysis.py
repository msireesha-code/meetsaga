from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.entities import Analysis, Job, Meeting
from app.schemas import AnalysisOut, JobOut
from app.workers.job_runner import submit_reanalysis_job

router = APIRouter(prefix="/api/meetings", tags=["analysis"])
settings = get_settings()


class ReanalyzeRequest(BaseModel):
    analysis_language: str | None = None


@router.get("/{meeting_id}/analysis", response_model=AnalysisOut)
def get_analysis(meeting_id: str, db: Session = Depends(get_db)):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.meeting_id == meeting_id, Analysis.is_current.is_(True))
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not available yet")
    return analysis


@router.get("/{meeting_id}/analysis/history", response_model=list[AnalysisOut])
def get_analysis_history(meeting_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Analysis)
        .filter(Analysis.meeting_id == meeting_id)
        .order_by(Analysis.version.desc())
        .all()
    )


@router.post("/{meeting_id}/reanalyze", response_model=JobOut)
def reanalyze(meeting_id: str, body: ReanalyzeRequest, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    job = Job(
        meeting_id=meeting_id,
        filename=meeting.original_filename,
        status="QUEUED",
        stage="QUEUED",
        analysis_requested=True,
        analysis_language=body.analysis_language or settings.default_analysis_language,
    )
    db.add(job)
    db.commit()
    submit_reanalysis_job(job.id)
    return job
