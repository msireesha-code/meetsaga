from sqlalchemy.orm import Session

from app.models.entities import RemoteProvider
from app.services.transcription.base import TranscriptionProvider, TranscriptionProviderError
from app.services.transcription.local_provider import LocalTranscriptionProvider
from app.services.transcription.remote_provider import RemoteTranscriptionProvider


def build_provider(
    db: Session,
    provider_name: str,
    model_override: str | None = None,
) -> TranscriptionProvider:
    """Single factory function the rest of the app uses to obtain a transcription
    provider. No other module should import a concrete provider class directly."""
    if provider_name == "local":
        return LocalTranscriptionProvider(model_name=model_override)

    remote = db.query(RemoteProvider).filter(RemoteProvider.name == provider_name).first()
    if not remote:
        raise TranscriptionProviderError(f"Unknown transcription provider '{provider_name}'", retryable=False)
    if model_override:
        remote.model = model_override
    return RemoteTranscriptionProvider(remote)
