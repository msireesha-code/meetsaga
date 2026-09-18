import json


def _fmt_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_vtt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def to_txt(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        speaker = seg.get("speaker_label") or "Unknown"
        lines.append(f"[{seg['start']:.2f} - {seg['end']:.2f}] {speaker}: {seg['text']}")
    return "\n".join(lines)


def to_srt(segments: list[dict]) -> str:
    blocks = []
    for i, seg in enumerate(segments, start=1):
        speaker = seg.get("speaker_label")
        text = f"{speaker}: {seg['text']}" if speaker else seg["text"]
        blocks.append(f"{i}\n{_fmt_srt_time(seg['start'])} --> {_fmt_srt_time(seg['end'])}\n{text}\n")
    return "\n".join(blocks)


def to_vtt(segments: list[dict]) -> str:
    blocks = ["WEBVTT\n"]
    for seg in segments:
        speaker = seg.get("speaker_label")
        text = f"{speaker}: {seg['text']}" if speaker else seg["text"]
        blocks.append(f"{_fmt_vtt_time(seg['start'])} --> {_fmt_vtt_time(seg['end'])}\n{text}\n")
    return "\n".join(blocks)


def to_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def to_markdown_transcript(segments: list[dict]) -> str:
    lines = ["# Transcript", ""]
    for seg in segments:
        speaker = seg.get("speaker_label") or "Unknown"
        lang = f" `[{seg['language']}]`" if seg.get("language") else ""
        lines.append(f"**{speaker}**{lang} ({seg['start']:.2f}s - {seg['end']:.2f}s): {seg['text']}")
        lines.append("")
    return "\n".join(lines)


def to_markdown_analysis(analysis: dict) -> str:
    lines = ["# Meeting Analysis", "", "## Executive Summary", analysis.get("summary", ""), ""]

    def section(title: str, items: list, formatter):
        lines.append(f"## {title}")
        if not items:
            lines.append("_None identified._")
        for item in items:
            lines.append(formatter(item))
        lines.append("")

    section("Key Discussion Points", analysis.get("key_discussion_points", []), lambda i: f"- {i}")
    section("Decisions", analysis.get("decisions", []), lambda i: f"- {i.get('decision', i)}")
    section(
        "Action Items",
        analysis.get("action_items", []),
        lambda i: f"- **{i.get('action')}** — Owner: {i.get('owner')}, Due: {i.get('due_date')}, "
        f"Priority: {i.get('priority')}, Timestamp: {i.get('timestamp') or 'N/A'}",
    )
    section("Open Issues", analysis.get("open_issues", []), lambda i: f"- {i.get('issue', i)}")
    section("Risks / Concerns", analysis.get("risks", []), lambda i: f"- {i.get('risk', i)}")
    section(
        "Important Dates",
        analysis.get("important_dates", []),
        lambda i: f"- {i.get('date', '')}: {i.get('description', '')}",
    )
    section("Questions / Follow-ups", analysis.get("questions", []), lambda i: f"- {i.get('question', i)}")

    return "\n".join(lines)
