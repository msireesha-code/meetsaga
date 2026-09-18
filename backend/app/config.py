from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MeetSage"
    data_dir: str = "./data"
    database_url: str = "sqlite:///./data/meetsage.db"
    default_analysis_language: str = "en"

    default_transcription_provider: str = "local"
    local_whisper_model: str = "small"
    local_whisper_device: str = "cpu"
    local_whisper_compute_type: str = "int8"
    local_whisper_cpu_threads: int = 0
    max_concurrent_jobs: int = 1

    diarization_enabled: bool = True
    huggingface_token: str = ""

    llm_provider: str = "openai-compatible"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2000
    llm_timeout_seconds: int = 120

    max_upload_size_mb: int = 2048

    # Comma-separated list of allowed CORS origins for the separately-hosted dev
    # frontend. Not consulted when the backend serves a built frontend itself
    # (same-origin requests don't need CORS at all) — see docs/deployment.md.
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def data_path(self) -> Path:
        base = Path(self.data_dir)
        if not base.is_absolute():
            base = Path(__file__).resolve().parents[2] / self.data_dir
        return base

    @property
    def uploads_dir(self) -> Path:
        return self.data_path / "uploads"

    @property
    def media_dir(self) -> Path:
        return self.data_path / "media"

    @property
    def transcripts_dir(self) -> Path:
        return self.data_path / "transcripts"

    @property
    def analysis_dir(self) -> Path:
        return self.data_path / "analysis"

    @property
    def exports_dir(self) -> Path:
        return self.data_path / "exports"

    @property
    def models_dir(self) -> Path:
        return self.data_path / "models"

    def ensure_directories(self) -> None:
        for d in (
            self.uploads_dir,
            self.media_dir,
            self.transcripts_dir,
            self.analysis_dir,
            self.exports_dir,
            self.models_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}

SUPPORTED_ANALYSIS_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}

SUPPORTED_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

SUPPORTED_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".flac", ".ogg", ".aac"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
