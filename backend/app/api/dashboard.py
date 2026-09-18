from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import ActionItem, Analysis, Job, Meeting
from app.schemas import DashboardStatsOut, MeetingOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsOut)
def dashboard_stats(db: Session = Depends(get_db)):
    total_meetings = db.query(func.count(Meeting.id)).scalar() or 0

    latest_job_status_subq = (
        db.query(Job.meeting_id, func.max(Job.created_at).label("max_created"))
        .group_by(Job.meeting_id)
        .subquery()
    )
    latest_jobs = (
        db.query(Job)
        .join(
            latest_job_status_subq,
            (Job.meeting_id == latest_job_status_subq.c.meeting_id)
            & (Job.created_at == latest_job_status_subq.c.max_created),
        )
        .all()
    )
    completed = sum(1 for j in latest_jobs if j.status == "COMPLETED")
    processing = sum(1 for j in latest_jobs if j.status not in {"COMPLETED", "FAILED", "CANCELLED"})
    failed = sum(1 for j in latest_jobs if j.status == "FAILED")

    total_duration = db.query(func.coalesce(func.sum(Meeting.duration_seconds), 0.0)).scalar() or 0.0
    total_action_items = db.query(func.count(ActionItem.id)).scalar() or 0

    return DashboardStatsOut(
        total_meetings=total_meetings,
        completed=completed,
        processing=processing,
        failed=failed,
        total_meeting_duration_seconds=float(total_duration),
        total_action_items=total_action_items,
    )


@router.get("/recent-meetings", response_model=list[MeetingOut])
def recent_meetings(db: Session = Depends(get_db), limit: int = 10):
    return db.query(Meeting).order_by(Meeting.created_at.desc()).limit(limit).all()
