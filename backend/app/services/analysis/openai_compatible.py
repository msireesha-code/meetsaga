import json
import logging
import re

from openai import APIError, APITimeoutError, OpenAI

from app.config import SUPPORTED_ANALYSIS_LANGUAGES, get_settings
from app.services.analysis.base import ActionItemResult, AnalysisError, AnalysisResult, MeetingAnalyzer
from app.services.analysis.chunking import chunk_segments
from app.services.analysis.prompts import (
    SYSTEM_PROMPT,
    build_chunk_prompt,
    build_synthesis_prompt,
    format_transcript_for_prompt,
)

logger = logging.getLogger("meetsage.analysis")

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json(raw: str) -> dict:
    cleaned = _JSON_FENCE.sub("", raw.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # last-ditch: find first {...last }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise AnalysisError("LLM returned a response that could not be parsed as JSON") from exc
        raise AnalysisError("LLM returned a response that could not be parsed as JSON")


def _seg_id_list(raw) -> list[int]:
    if not isinstance(raw, list):
        return []
    out = []
    for v in raw:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


class OpenAICompatibleAnalyzer(MeetingAnalyzer):
    name = "openai-compatible"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key or "not-required"
        self.model = model or settings.llm_model
        self.temperature = settings.llm_temperature if temperature is None else temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.timeout_seconds = timeout_seconds or settings.llm_timeout_seconds

        if "api.openai.com" in self.base_url and self.api_key in ("", "not-required"):
            raise AnalysisError(
                "No LLM API key configured. Set LLM_API_KEY in .env (or point LLM_BASE_URL at a "
                "local/office-hosted OpenAI-compatible server that doesn't require one), then use "
                "'Re-run Analysis' on this meeting.",
                retryable=False,
            )

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout_seconds)

    def _call(self, user_prompt: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except APITimeoutError as exc:
            raise AnalysisError(f"LLM request timed out after {self.timeout_seconds}s", retryable=True) from exc
        except APIError as exc:
            raise AnalysisError(f"LLM provider error: {exc}", retryable=True) from exc

        content = response.choices[0].message.content or ""
        return _extract_json(content)

    def analyze(self, segments: list[dict], analysis_language: str) -> AnalysisResult:
        lang_name = SUPPORTED_ANALYSIS_LANGUAGES.get(analysis_language, "English")
        chunks = chunk_segments(segments)

        partials: list[dict] = []
        for chunk in chunks:
            if not chunk:
                continue
            transcript_text = format_transcript_for_prompt(chunk)
            prompt = build_chunk_prompt(transcript_text, lang_name)
            partials.append(self._call(prompt))

        if not partials:
            return AnalysisResult(summary="", provider=self.name, model=self.model)

        if len(partials) == 1:
            final_summary = partials[0].get("summary", "")
        else:
            synth_prompt = build_synthesis_prompt([p.get("summary", "") for p in partials], lang_name)
            synth = self._call(synth_prompt)
            final_summary = synth.get("summary", "")

        result = AnalysisResult(summary=final_summary, provider=self.name, model=self.model)

        for p in partials:
            result.key_discussion_points.extend(p.get("key_discussion_points", []) or [])
            result.decisions.extend(
                {"decision": d.get("decision", ""), "source_segment_ids": _seg_id_list(d.get("source_segment_ids"))}
                for d in (p.get("decisions") or [])
            )
            result.open_issues.extend(
                {"issue": d.get("issue", ""), "source_segment_ids": _seg_id_list(d.get("source_segment_ids"))}
                for d in (p.get("open_issues") or [])
            )
            result.risks.extend(
                {"risk": d.get("risk", ""), "source_segment_ids": _seg_id_list(d.get("source_segment_ids"))}
                for d in (p.get("risks") or [])
            )
            result.important_dates.extend(
                {
                    "date": d.get("date", ""),
                    "description": d.get("description", ""),
                    "source_segment_ids": _seg_id_list(d.get("source_segment_ids")),
                }
                for d in (p.get("important_dates") or [])
            )
            result.questions.extend(
                {"question": d.get("question", ""), "source_segment_ids": _seg_id_list(d.get("source_segment_ids"))}
                for d in (p.get("questions") or [])
            )
            for a in p.get("action_items", []) or []:
                result.action_items.append(
                    ActionItemResult(
                        action=a.get("action", ""),
                        owner=a.get("owner") or "Not specified",
                        due_date=a.get("due_date") or "Not specified",
                        priority=a.get("priority") or "Not specified",
                        source_segment_ids=_seg_id_list(a.get("source_segment_ids")),
                        context=a.get("context"),
                    )
                )

        return result
