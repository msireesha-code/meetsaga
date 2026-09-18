from datetime import datetime

from pydantic import BaseModel, Field


class MeetingCreateResponse(BaseModel):
    meeting_id: str
    job_id: str


class MediaOut(BaseModel):
    id: str
    original_path: str
    normalized_audio_path: str | None
    mime_type: str | None
    duration_seconds: float | None
    sample_rate: int | None
    channels: int | None
    codec: str | None

    class Config:
        from_attributes = True


class MeetingOut(BaseModel):
    id: str
    name: str
    original_filename: str
    media_type: str
    expected_languages: list[str]
    auto_detect_languages: bool
    duration_seconds: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: str
    meeting_id: str
    filename: str
    status: str
    stage: str
    progress: float | None
    started_at: datetime | None
    ended_at: datetime | None
    error: str | None
    transcription_provider: str | None
    transcription_model: str | None
    analysis_provider: str | None
    analysis_model: str | None
    transcription_duration_seconds: float | None
    diarization_duration_seconds: float | None
    analysis_duration_seconds: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptSegmentOut(BaseModel):
    id: str
    seq: int
    start: float
    end: float
    speaker_label: str | None
    language: str | None
    text: str

    class Config:
        from_attributes = True


class TranscriptOut(BaseModel):
    id: str
    version: int
    provider: str | None
    model: str | None
    languages_detected: list[str]
    diarization_status: str
    segments: list[TranscriptSegmentOut]

    class Config:
        from_attributes = True


class SpeakerOut(BaseModel):
    id: str
    label: str
    display_name: str | None

    class Config:
        from_attributes = True


class SpeakerRenameRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)


class ActionItemOut(BaseModel):
    id: str
    action: str
    owner: str
    due_date: str
    priority: str
    timestamp: str | None
    source_segment_ids: list[int]
    context: str | None

    class Config:
        from_attributes = True


class AnalysisOut(BaseModel):
    id: str
    version: int
    provider: str | None
    model: str | None
    language: str
    summary: str | None
    key_discussion_points: list
    decisions: list
    open_issues: list
    risks: list
    important_dates: list
    questions: list
    action_items: list[ActionItemOut]
    created_at: datetime

    class Config:
        from_attributes = True


class RemoteProviderCreate(BaseModel):
    name: str
    base_url: str
    endpoint_path: str = "/v1/audio/transcriptions"
    model: str | None = None
    api_token: str | None = None
    auth_method: str = "bearer"
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 300.0
    total_timeout_seconds: float = 600.0
    tls_verify: bool = True


class RemoteProviderOut(BaseModel):
    id: str
    name: str
    base_url: str
    endpoint_path: str
    model: str | None
    auth_method: str
    connect_timeout_seconds: float
    read_timeout_seconds: float
    total_timeout_seconds: float
    tls_verify: bool
    api_token_masked: str

    class Config:
        from_attributes = True


class TestConnectionResult(BaseModel):
    success: bool
    message: str


class SystemStatusOut(BaseModel):
    meetsage_version: str
    python_version: str
    ffmpeg_version: str | None
    ffprobe_version: str | None
    cpu_count: int
    ram_total_gb: float
    ram_available_gb: float
    disk_total_gb: float
    disk_free_gb: float
    installed_models: list[str]


class DashboardStatsOut(BaseModel):
    total_meetings: int
    completed: int
    processing: int
    failed: int
    total_meeting_duration_seconds: float
    total_action_items: int
