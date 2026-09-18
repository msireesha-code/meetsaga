import logging
import threading
from pathlib import Path

from app.config import get_settings
from app.services.transcription.base import (
    TranscriptionProvider,
    TranscriptionProviderError,
    TranscriptionResult,
    TranscriptSegmentResult,
)
from app.services.transcription.language_id import detect_segment_language

logger = logging.getLogger("meetsage.transcription.local")

_model_cache: dict[str, object] = {}
_model_lock = threading.Lock()

SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3"]


def _load_model(model_name: str, device: str, compute_type: str, cpu_threads: int):
    from faster_whisper import WhisperModel

    key = f"{model_name}:{device}:{compute_type}:{cpu_threads}"
    with _model_lock:
        if key not in _model_cache:
            settings = get_settings()
            settings.models_dir.mkdir(parents=True, exist_ok=True)
            logger.info("loading faster-whisper model", extra={"model": model_name})
            _model_cache[key] = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads or 0,
                download_root=str(settings.models_dir),
            )
        return _model_cache[key]


class LocalTranscriptionProvider(TranscriptionProvider):
    name = "local"

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        cpu_threads: int | None = None,
    ):
        settings = get_settings()
        self.model_name = model_name or settings.local_whisper_model
        self.device = device or settings.local_whisper_device
        self.compute_type = compute_type or settings.local_whisper_compute_type
        self.cpu_threads = cpu_threads if cpu_threads is not None else settings.local_whisper_cpu_threads

    def transcribe(
        self,
        audio_path: Path,
        expected_languages: list[str],
        auto_detect_languages: bool = False,
        progress_callback=None,
    ) -> TranscriptionResult:
        try:
            model = _load_model(self.model_name, self.device, self.compute_type, self.cpu_threads)
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionProviderError(
                f"Failed to load local Whisper model '{self.model_name}': {exc}", retryable=True
            ) from exc

        is_multilingual_meeting = len(expected_languages) > 1 or auto_detect_languages

        try:
            segments_iter, info = model.transcribe(
                str(audio_path),
                language=None,  # always auto-detect; we never force a single language
                task="transcribe",
                multilingual=is_multilingual_meeting,
                # VAD filtering was silently dropping real speech (confirmed: on a
                # real meeting recording it skipped ~12s of continuous dialogue
                # mid-segment, misclassified as silence). faster-whisper's own
                # no_speech_threshold (default 0.6) already suppresses genuine
                # silence per-window without VAD's coarser speech/non-speech cut,
                # so we rely on that instead. See docs/troubleshooting.md.
                vad_filter=False,
                condition_on_previous_text=True,
            )

            duration = info.duration or 0.0
            results: list[TranscriptSegmentResult] = []
            languages_seen: set[str] = set()
            for seg in segments_iter:
                if progress_callback and duration > 0:
                    try:
                        progress_callback(min(1.0, max(0.0, seg.end / duration)))
                    except Exception:  # noqa: BLE001
                        pass  # progress reporting must never break transcription
                text = seg.text.strip()
                if not text:
                    continue
                lang = detect_segment_language(text, expected_languages or ["en"])
                languages_seen.add(lang)
                results.append(TranscriptSegmentResult(start=seg.start, end=seg.end, text=text, language=lang))
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionProviderError(f"Local transcription failed: {exc}", retryable=True) from exc

        if not languages_seen and info.language:
            languages_seen.add(info.language)

        return TranscriptionResult(
            segments=results,
            languages_detected=sorted(languages_seen),
            provider=self.name,
            model=self.model_name,
        )
