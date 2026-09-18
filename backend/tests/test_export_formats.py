import json

from app.services.export.formats import (
    to_json,
    to_markdown_analysis,
    to_markdown_transcript,
    to_srt,
    to_txt,
    to_vtt,
)

SEGMENTS = [
    {"start": 0.0, "end": 3.8, "speaker_label": "SPEAKER_00", "language": "en", "text": "Hello world."},
    {"start": 3.8, "end": 7.0, "speaker_label": "SPEAKER_01", "language": "hi", "text": "नमस्ते."},
]


def test_to_txt_contains_all_segments():
    out = to_txt(SEGMENTS)
    assert "Hello world." in out
    assert "नमस्ते." in out


def test_to_srt_format():
    out = to_srt(SEGMENTS)
    assert out.strip().startswith("1")
    assert "00:00:00,000 --> 00:00:03,800" in out


def test_to_vtt_format():
    out = to_vtt(SEGMENTS)
    assert out.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:03.800" in out


def test_to_json_roundtrip():
    out = to_json({"segments": SEGMENTS})
    parsed = json.loads(out)
    assert len(parsed["segments"]) == 2


def test_to_markdown_transcript_includes_language_tags():
    out = to_markdown_transcript(SEGMENTS)
    assert "[hi]" in out


def test_to_markdown_analysis_handles_empty_sections():
    out = to_markdown_analysis({"summary": "Test summary", "action_items": []})
    assert "Test summary" in out
    assert "None identified" in out


def test_to_markdown_analysis_renders_action_items():
    out = to_markdown_analysis(
        {
            "summary": "s",
            "action_items": [
                {"action": "Ship it", "owner": "Ravi", "due_date": "Friday", "priority": "High", "timestamp": "00:01:00"}
            ],
        }
    )
    assert "Ship it" in out
    assert "Ravi" in out
