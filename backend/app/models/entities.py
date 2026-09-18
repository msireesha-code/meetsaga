import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)  # audio | video
    expected_languages: Mapped[list] = mapped_column(JSON, default=list)
    auto_detect_languages: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    media = relationship("Media", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="meeting", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="meeting", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="meeting", cascade="all, delete-orphan")


class Media(Base):
    __tablename__ = "media"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    original_path: Mapped[str] = mapped_column(String, nullable=False)
    normalized_audio_path: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codec: Mapped[str | None] = mapped_column(String, nullable=True)
    ffprobe_raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    meeting = relationship("Meeting", back_populates="media")


JOB_STATES = [
    "QUEUED",
    "VALIDATING",
    "MEDIA_ANALYSIS",
    "PREPROCESSING",
    "TRANSCRIBING",
    "DIARIZING",
    "ANALYZING",
    "EXPORTING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="QUEUED")
    stage: Mapped[str] = mapped_column(String, default="QUEUED")
    progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    transcription_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    transcription_model: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_model: Mapped[str | None] = mapped_column(String, nullable=True)

    diarization_requested: Mapped[bool] = mapped_column(Boolean, default=True)
    analysis_requested: Mapped[bool] = mapped_column(Boolean, default=True)
    analysis_language: Mapped[str] = mapped_column(String, default="en")

    transcription_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    diarization_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    meeting = relationship("Meeting", back_populates="jobs")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    languages_detected: Mapped[list] = mapped_column(JSON, default=list)
    diarization_status: Mapped[str] = mapped_column(String, default="not_run")  # not_run|running|completed|failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    meeting = relationship("Meeting", back_populates="transcripts")
    segments = relationship(
        "TranscriptSegment",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.start",
    )


class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)  # e.g. SPEAKER_00
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)

    meeting = relationship("Meeting", back_populates="speakers")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    start: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[float] = mapped_column(Float, nullable=False)
    speaker_label: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    transcript = relationship("Transcript", back_populates="segments")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, default="en")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_discussion_points: Mapped[list] = mapped_column(JSON, default=list)
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    open_issues: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    important_dates: Mapped[list] = mapped_column(JSON, default=list)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    meeting = relationship("Meeting", back_populates="analyses")
    action_items = relationship("ActionItem", back_populates="analysis", cascade="all, delete-orphan")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String, default="Not specified")
    due_date: Mapped[str] = mapped_column(String, default="Not specified")
    priority: Mapped[str] = mapped_column(String, default="Not specified")
    timestamp: Mapped[str | None] = mapped_column(String, nullable=True)
    source_segment_ids: Mapped[list] = mapped_column(JSON, default=list)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis = relationship("Analysis", back_populates="action_items")


class RemoteProvider(Base):
    __tablename__ = "remote_providers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    endpoint_path: Mapped[str] = mapped_column(String, default="/v1/audio/transcriptions")
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    api_token: Mapped[str | None] = mapped_column(String, nullable=True)
    auth_method: Mapped[str] = mapped_column(String, default="bearer")
    connect_timeout_seconds: Mapped[float] = mapped_column(Float, default=10.0)
    read_timeout_seconds: Mapped[float] = mapped_column(Float, default=300.0)
    total_timeout_seconds: Mapped[float] = mapped_column(Float, default=600.0)
    tls_verify: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
