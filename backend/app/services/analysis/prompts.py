SYSTEM_PROMPT = """You are a meeting-analysis assistant. You extract structured information from a
meeting transcript. You must be conservative and factual.

STRICT RULES:
- Never invent an action-item owner, due date, priority, decision, or fact that was not stated.
- If an owner is not explicitly named, set "owner" to "Not specified".
- If a due date is not explicitly stated, set "due_date" to "Not specified".
- If a priority is not explicitly stated, set "priority" to "Not specified" (do not guess "Medium" as a default).
- Every action item, decision, open issue, risk, date, and question MUST include "source_segment_ids":
  an array of the integer segment IDs (shown as [id=N] in the transcript) that support it.
- Do not translate or alter quoted text; you may summarize in the requested analysis language.
- Respond with ONLY a single JSON object. No markdown, no commentary, no code fences.
"""

RESPONSE_SCHEMA_HINT = """
Respond with a JSON object with exactly these keys:
{
  "summary": "string, executive summary in the requested language",
  "key_discussion_points": ["string", ...],
  "decisions": [{"decision": "string", "source_segment_ids": [int]}],
  "action_items": [{"action": "string", "owner": "string", "due_date": "string", "priority": "string",
                     "source_segment_ids": [int], "context": "string"}],
  "open_issues": [{"issue": "string", "source_segment_ids": [int]}],
  "risks": [{"risk": "string", "source_segment_ids": [int]}],
  "important_dates": [{"date": "string", "description": "string", "source_segment_ids": [int]}],
  "questions": [{"question": "string", "source_segment_ids": [int]}]
}
"""


def build_chunk_prompt(transcript_text: str, analysis_language_name: str) -> str:
    return (
        f"Analyze the following meeting transcript excerpt. Write the summary and any narrative "
        f"text in {analysis_language_name}. Keep quoted transcript content as-is.\n\n"
        f"{RESPONSE_SCHEMA_HINT}\n\nTRANSCRIPT EXCERPT:\n{transcript_text}\n"
    )


def build_synthesis_prompt(partial_summaries: list[str], analysis_language_name: str) -> str:
    joined = "\n\n---\n\n".join(f"Part {i+1} summary:\n{s}" for i, s in enumerate(partial_summaries))
    return (
        f"The following are summaries of consecutive parts of one meeting, in order. "
        f"Write ONE coherent executive summary of the whole meeting in {analysis_language_name}. "
        f"Respond with ONLY a JSON object: {{\"summary\": \"string\"}}\n\n{joined}"
    )


def format_transcript_for_prompt(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        speaker = seg.get("speaker_label") or "UNKNOWN"
        ts = seg.get("timestamp_str", "")
        lines.append(f"[id={seg['id']}] {ts} {speaker}: {seg['text']}")
    return "\n".join(lines)
