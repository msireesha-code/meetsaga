"""Regression test for a real bug found on 2026-09-09: faster-whisper's VAD
filter was silently dropping real speech (confirmed on an actual meeting
recording — it skipped ~12s of continuous dialogue, misclassified as silence).
This locks in that vad_filter must stay disabled.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import app.services.transcription.local_provider as local_provider
from app.services.transcription.local_provider import LocalTranscriptionProvider


def test_transcribe_never_enables_vad_filter(monkeypatch, tmp_path):
    fake_info = SimpleNamespace(duration=10.0, language="en")
    fake_model = MagicMock()
    fake_model.transcribe.return_value = ([], fake_info)

    monkeypatch.setattr(local_provider, "_load_model", lambda *a, **k: fake_model)

    provider = LocalTranscriptionProvider(model_name="tiny")
    provider.transcribe(tmp_path / "audio.wav", expected_languages=["en", "hi", "te"])

    _, kwargs = fake_model.transcribe.call_args
    assert kwargs["vad_filter"] is False, (
        "vad_filter must stay disabled — it was found to silently drop real speech "
        "(see comment in local_provider.py and docs/troubleshooting.md)"
    )
