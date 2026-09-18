from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import ActionItem, Analysis, Meeting, Speaker, TranscriptSegment

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(q: str, db: Session = Depends(get_db), limit: int = 25):
    """Simple LIKE-based full-text search across meetings, transcripts, analysis,
    action items, and speakers. The architecture allows this to be swapped for a
    proper FTS5 index later without changing the API contract."""
    like = f"%{q}%"
    results = {"meetings": [], "transcript_segments": [], "analyses": [], "action_items": [], "speakers": []}

    for m in (
        db.query(Meeting)
        .filter((Meeting.name.ilike(like)) | (Meeting.original_filename.ilike(like)))
        .limit(limit)
        .all()
    ):
        results["meetings"].append({"id": m.id, "name": m.name})

    for seg in db.query(TranscriptSegment).filter(TranscriptSegment.text.ilike(like)).limit(limit).all():
        results["transcript_segments"].append(
            {
                "id": seg.id,
                "transcript_id": seg.transcript_id,
                "text": seg.text,
                "start": seg.start,
            }
        )

    for a in db.query(Analysis).filter(Analysis.summary.ilike(like)).limit(limit).all():
        results["analyses"].append({"id": a.id, "meeting_id": a.meeting_id, "summary": a.summary})

    for ai in db.query(ActionItem).filter(ActionItem.action.ilike(like)).limit(limit).all():
        results["action_items"].append({"id": ai.id, "action": ai.action, "owner": ai.owner})

    for sp in db.query(Speaker).filter(Speaker.display_name.ilike(like)).limit(limit).all():
        results["speakers"].append({"id": sp.id, "display_name": sp.display_name, "label": sp.label})

    return results
