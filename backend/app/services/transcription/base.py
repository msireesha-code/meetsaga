from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

ProgressCallback = Optional[Callable[[float], None]]


@dataclass
class TranscriptSegmentResult:
    start: float
    end: float
    text: str
    language: str | None = None


@dataclass
class TranscriptionResult:
    segments: list[TranscriptSegmentResult]
    languages_detected: list[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""


class TranscriptionProvider(ABC):
    """All transcription backends implement this interface. The rest of the
    application must interact only through this abstraction — no provider-specific
    logic should live outside app/services/transcription/."""

    name: str = "base"

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        expected_languages: list[str],
        auto_detect_languages: bool = False,
        progress_callback: ProgressCallback = None,
    ) -> TranscriptionResult:
        """progress_callback, if given, is invoked with a real fraction (0..1) of
        audio duration actually processed so far. Providers that cannot report
        incremental progress (e.g. a single remote HTTP call) may ignore it —
        never fabricate a fraction that isn't backed by real processed audio."""
        raise NotImplementedError


class TranscriptionProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable
