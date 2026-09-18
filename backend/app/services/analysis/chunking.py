"""Splits long transcripts into LLM-context-sized chunks by segment count/character
budget, preserving segment IDs so downstream analysis can still cite sources.
Does NOT truncate — every segment is included in exactly one chunk."""

DEFAULT_MAX_CHARS_PER_CHUNK = 12000


def chunk_segments(segments: list[dict], max_chars: int = DEFAULT_MAX_CHARS_PER_CHUNK) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0

    for seg in segments:
        seg_len = len(seg["text"]) + 40
        if current and current_chars + seg_len > max_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(seg)
        current_chars += seg_len

    if current:
        chunks.append(current)

    return chunks or [[]]
