from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Analysis, Meeting, Speaker, Transcript
from app.services.export.formats import (
    to_json,
    to_markdown_analysis,
    to_markdown_transcript,
    to_srt,
    to_txt,
    to_vtt,
)

router = APIRouter(prefix="/api/meetings", tags=["exports"])

_MEDIA_TYPES = {
    "txt": "text/plain",
    "srt": "application/x-subrip",
    "vtt": "text/vtt",
    "json": "application/json",
    "md": "text/markdown",
}


def _segments_as_dicts(db: Session, meeting_id: str, transcript: Transcript) -> list[dict]:
    speaker_names = {
        s.label: s.display_name
        for s in db.query(Speaker).filter(Speaker.meeting_id == meeting_id).all()
        if s.display_name
    }
    return [
        {
            "start": s.start,
            "end": s.end,
            "speaker_label": speaker_names.get(s.speaker_label, s.speaker_label),
            "language": s.language,
            "text": s.text,
        }
        for s in transcript.segments
    ]


@router.get("/{meeting_id}/export/transcript")
def export_transcript(meeting_id: str, format: str = "txt", db: Session = Depends(get_db)):
    if format not in _MEDIA_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{format}'")
    transcript = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.version.desc())
        .first()
    )
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not available")

    segments = _segments_as_dicts(db, meeting_id, transcript)
    if format == "txt":
        body = to_txt(segments)
    elif format == "srt":
        body = to_srt(segments)
    elif format == "vtt":
        body = to_vtt(segments)
    elif format == "md":
        body = to_markdown_transcript(segments)
    else:
        body = to_json({"meeting_id": meeting_id, "segments": segments})

    filename = f"transcript_{meeting_id}.{format}"
    return Response(
        content=body,
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{meeting_id}/export/analysis")
def export_analysis(meeting_id: str, format: str = "json", db: Session = Depends(get_db)):
    if format not in {"json", "md"}:
        raise HTTPException(status_code=400, detail="Analysis export supports 'json' or 'md'")
    analysis = (
        db.query(Analysis)
        .filter(Analysis.meeting_id == meeting_id, Analysis.is_current.is_(True))
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not available")

    payload = {
        "summary": analysis.summary,
        "key_discussion_points": analysis.key_discussion_points,
        "decisions": analysis.decisions,
        "action_items": [
            {
                "action": ai.action,
                "owner": ai.owner,
                "due_date": ai.due_date,
                "priority": ai.priority,
                "timestamp": ai.timestamp,
                "source_segment_ids": ai.source_segment_ids,
                "context": ai.context,
            }
            for ai in analysis.action_items
        ],
        "open_issues": analysis.open_issues,
        "risks": analysis.risks,
        "important_dates": analysis.important_dates,
        "questions": analysis.questions,
    }

    body = to_json(payload) if format == "json" else to_markdown_analysis(payload)
    filename = f"analysis_{meeting_id}.{format}"
    return Response(
        content=body,
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
