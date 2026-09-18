from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Job
from app.schemas import JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), status: str | None = None, limit: int = 100):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    return query.order_by(Job.created_at.desc()).limit(limit).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {"COMPLETED", "FAILED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail=f"Job already {job.status.lower()}")
    if job.status == "QUEUED":
        job.status = "CANCELLED"
        job.stage = "CANCELLED"
        db.commit()
        return job
    raise HTTPException(
        status_code=400,
        detail="Job is already running and cannot be safely interrupted mid-stage; it will finish or fail on its own.",
    )
