import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("meetsage.diarization")

_pipeline_cache = {}
_pipeline_lock = threading.Lock()


class DiarizationError(RuntimeError):
    pass


@dataclass
class SpeakerTurn:
    start: float
    end: float
    speaker: str  # e.g. SPEAKER_00


def _get_pipeline():
    settings = get_settings()
    if not settings.huggingface_token:
        raise DiarizationError(
            "No Hugging Face token configured. Set HUGGINGFACE_TOKEN in .env and accept the "
            "license terms for pyannote/speaker-diarization-3.1 on huggingface.co."
        )
    with _pipeline_lock:
        if "pipeline" not in _pipeline_cache:
            from pyannote.audio import Pipeline

            logger.info("loading pyannote speaker-diarization pipeline")
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=settings.huggingface_token,
            )
            _pipeline_cache["pipeline"] = pipeline
        return _pipeline_cache["pipeline"]


def diarize(audio_path: Path) -> list[SpeakerTurn]:
    """Run speaker diarization. Raises DiarizationError on any failure — callers
    must treat this as independent/optional: a failure here must NOT fail the
    overall job, only the diarization stage (see JOB spec: diarization failures
    keep the transcript available and are retryable)."""
    try:
        import torch
        import soundfile as sf

        pipeline = _get_pipeline()
        # Load the audio ourselves via soundfile and hand pyannote a waveform
        # tensor directly, bypassing torchcodec (which fails to load its native
        # extension in this environment — see docs/troubleshooting.md).
        audio_array, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=True)
        waveform = torch.from_numpy(audio_array.T)  # (channels, time)
        diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})
    except DiarizationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DiarizationError(f"Diarization failed: {exc}") from exc

    # pyannote-audio >=4.0 wraps the result in a DiarizeOutput dataclass whose
    # `.speaker_diarization` is the Annotation; <4.0 returned the Annotation
    # directly. Support both so a future pyannote upgrade doesn't silently break.
    annotation = getattr(diarization, "speaker_diarization", diarization)

    turns: list[SpeakerTurn] = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        turns.append(SpeakerTurn(start=turn.start, end=turn.end, speaker=speaker))
    return turns


def assign_speakers_to_segments(segments: list[dict], turns: list[SpeakerTurn]) -> None:
    """Mutates each segment dict in place, adding 'speaker_label' based on maximum
    temporal overlap with diarization turns. Segments with no overlapping turn are
    left with speaker_label=None rather than guessed."""
    for seg in segments:
        best_turn = None
        best_overlap = 0.0
        for turn in turns:
            overlap = min(seg["end"], turn.end) - max(seg["start"], turn.start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_turn = turn
        seg["speaker_label"] = best_turn.speaker if best_turn else None
