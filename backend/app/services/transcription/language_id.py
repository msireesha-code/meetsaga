"""Best-effort per-segment language tagging using Unicode script detection.

Whisper (via faster-whisper) does not expose a per-segment language label through
its public API — language detection happens once per ~30s audio window internally
and is not surfaced per output segment. Rather than fabricate confidence we do not
have, we tag each segment with the *dominant script* actually present in the text
Whisper produced. This is deterministic and derived only from the transcribed text
itself — it never alters or guesses at the transcript content.

For a code-switched segment (e.g. English words inside a Hindi sentence) this
reports the dominant language, not per-word attribution. That limitation is
documented in docs/troubleshooting.md and docs/faq.md.
"""
import re

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_TELUGU = re.compile(r"[ఀ-౿]")
_LATIN_WORD = re.compile(r"[A-Za-z]")


def detect_segment_language(text: str, expected_languages: list[str]) -> str:
    hindi_chars = len(_DEVANAGARI.findall(text))
    telugu_chars = len(_TELUGU.findall(text))
    latin_chars = len(_LATIN_WORD.findall(text))

    counts = {"hi": hindi_chars, "te": telugu_chars, "en": latin_chars}
    dominant = max(counts, key=counts.get)

    if counts[dominant] == 0:
        return "en" if "en" in expected_languages else (expected_languages[0] if expected_languages else "en")

    if dominant not in expected_languages and expected_languages:
        return dominant  # honest tag even if user didn't expect it (e.g. auto-detect)

    return dominant
