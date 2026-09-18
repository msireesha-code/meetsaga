import json
from unittest.mock import MagicMock

import pytest

from app.services.analysis.base import AnalysisError
from app.services.analysis.openai_compatible import OpenAICompatibleAnalyzer

SEGMENTS = [
    {"id": 0, "text": "Someone should do the thing.", "speaker_label": None, "timestamp_str": "00:00:00", "start": 0.0}
]


def _mock_response(content: dict | str):
    body = content if isinstance(content, str) else json.dumps(content)
    msg = MagicMock()
    msg.content = body
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _analyzer():
    return OpenAICompatibleAnalyzer(base_url="http://fake-llm.local/v1", api_key="test-key", model="test-model")


def test_rejects_missing_api_key_for_real_openai_endpoint():
    with pytest.raises(AnalysisError):
        OpenAICompatibleAnalyzer(base_url="https://api.openai.com/v1", api_key="")


def test_missing_owner_defaults_to_not_specified():
    analyzer = _analyzer()
    analyzer.client.chat.completions.create = MagicMock(
        return_value=_mock_response(
            {
                "summary": "Test meeting summary",
                "key_discussion_points": [],
                "decisions": [],
                "action_items": [{"action": "Do the thing", "source_segment_ids": [0]}],
                "open_issues": [],
                "risks": [],
                "important_dates": [],
                "questions": [],
            }
        )
    )
    result = analyzer.analyze(SEGMENTS, "en")
    item = result.action_items[0]
    assert item.owner == "Not specified"
    assert item.due_date == "Not specified"
    assert item.priority == "Not specified"


def test_action_item_preserves_explicit_fields():
    analyzer = _analyzer()
    analyzer.client.chat.completions.create = MagicMock(
        return_value=_mock_response(
            {
                "summary": "s",
                "key_discussion_points": [],
                "decisions": [],
                "action_items": [
                    {"action": "Ship it", "owner": "Ravi", "due_date": "Friday", "priority": "High", "source_segment_ids": [0]}
                ],
                "open_issues": [],
                "risks": [],
                "important_dates": [],
                "questions": [],
            }
        )
    )
    result = analyzer.analyze(SEGMENTS, "en")
    item = result.action_items[0]
    assert item.owner == "Ravi"
    assert item.due_date == "Friday"
    assert item.priority == "High"


def test_json_wrapped_in_markdown_fence_is_parsed():
    analyzer = _analyzer()
    fenced = "```json\n" + json.dumps({"summary": "fenced summary", "action_items": []}) + "\n```"
    analyzer.client.chat.completions.create = MagicMock(return_value=_mock_response(fenced))
    result = analyzer.analyze(SEGMENTS, "en")
    assert result.summary == "fenced summary"


def test_unparseable_response_raises_analysis_error():
    analyzer = _analyzer()
    analyzer.client.chat.completions.create = MagicMock(return_value=_mock_response("not json at all"))
    with pytest.raises(AnalysisError):
        analyzer.analyze(SEGMENTS, "en")


def test_multi_chunk_preserves_action_items_from_every_chunk(monkeypatch):
    analyzer = _analyzer()
    # Force two chunks regardless of size, so we can verify the "no items lost
    # across chunks" requirement (spec section 20).
    monkeypatch.setattr(
        "app.services.analysis.openai_compatible.chunk_segments",
        lambda segments, max_chars=None: [[segments[0]], [segments[0]]],
    )
    responses = [
        _mock_response({"summary": "part 1", "action_items": [{"action": "Task A", "source_segment_ids": [0]}]}),
        _mock_response({"summary": "part 2", "action_items": [{"action": "Task B", "source_segment_ids": [0]}]}),
        _mock_response({"summary": "final synthesis"}),
    ]
    analyzer.client.chat.completions.create = MagicMock(side_effect=responses)
    result = analyzer.analyze(SEGMENTS, "en")
    actions = {a.action for a in result.action_items}
    assert actions == {"Task A", "Task B"}
    assert result.summary == "final synthesis"
