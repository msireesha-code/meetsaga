import logging
from pathlib import Path

import httpx

from app.models.entities import RemoteProvider
from app.services.transcription.base import (
    TranscriptionProvider,
    TranscriptionProviderError,
    TranscriptionResult,
    TranscriptSegmentResult,
)
from app.services.transcription.language_id import detect_segment_language

logger = logging.getLogger("meetsage.transcription.remote")


class RemoteTranscriptionProvider(TranscriptionProvider):
    """Calls an OpenAI-compatible Whisper HTTP endpoint. This class is the ONLY
    place remote transcription HTTP calls are made — always backend-side, never
    from the browser. The API token is never logged and never echoed back."""

    name = "remote"

    def __init__(self, provider_config: RemoteProvider):
        self.config = provider_config

    def transcribe(
        self,
        audio_path: Path,
        expected_languages: list[str],
        auto_detect_languages: bool = False,
        progress_callback=None,
    ) -> TranscriptionResult:
        cfg = self.config
        url = cfg.base_url.rstrip("/") + cfg.endpoint_path
        headers = {}
        if cfg.api_token:
            if cfg.auth_method == "bearer":
                headers["Authorization"] = f"Bearer {cfg.api_token}"
            else:
                headers[cfg.auth_method] = cfg.api_token

        timeout = httpx.Timeout(
            connect=cfg.connect_timeout_seconds,
            read=cfg.read_timeout_seconds,
            write=cfg.read_timeout_seconds,
            pool=cfg.total_timeout_seconds,
        )

        try:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/wav")}
                data = {}
                if cfg.model:
                    data["model"] = cfg.model
                data["response_format"] = "verbose_json"

                with httpx.Client(verify=cfg.tls_verify, timeout=timeout) as client:
                    response = client.post(url, headers=headers, files=files, data=data)
        except httpx.TimeoutException as exc:
            raise TranscriptionProviderError(
                f"Remote provider '{cfg.name}' timed out", retryable=True
            ) from exc
        except httpx.RequestError as exc:
            raise TranscriptionProviderError(
                f"Could not reach remote provider '{cfg.name}': {exc.__class__.__name__}", retryable=True
            ) from exc

        if response.status_code != 200:
            raise TranscriptionProviderError(
                f"Remote provider '{cfg.name}' returned HTTP {response.status_code}", retryable=True
            )

        body = response.json()
        raw_segments = body.get("segments")
        results: list[TranscriptSegmentResult] = []
        languages_seen: set[str] = set()

        if raw_segments:
            for seg in raw_segments:
                text = (seg.get("text") or "").strip()
                if not text:
                    continue
                lang = detect_segment_language(text, expected_languages or ["en"])
                languages_seen.add(lang)
                results.append(
                    TranscriptSegmentResult(
                        start=float(seg.get("start", 0.0)),
                        end=float(seg.get("end", 0.0)),
                        text=text,
                        language=lang,
                    )
                )
        else:
            text = (body.get("text") or "").strip()
            if text:
                lang = detect_segment_language(text, expected_languages or ["en"])
                languages_seen.add(lang)
                results.append(TranscriptSegmentResult(start=0.0, end=0.0, text=text, language=lang))

        return TranscriptionResult(
            segments=results,
            languages_detected=sorted(languages_seen),
            provider=self.name,
            model=cfg.model or "",
        )


def test_connection(provider_config: RemoteProvider) -> tuple[bool, str]:
    """Best-effort connectivity check against GET /v1/models (optional per spec)."""
    url = provider_config.base_url.rstrip("/") + "/v1/models"
    headers = {}
    if provider_config.api_token:
        headers["Authorization"] = f"Bearer {provider_config.api_token}"
    try:
        with httpx.Client(verify=provider_config.tls_verify, timeout=provider_config.connect_timeout_seconds) as client:
            resp = client.get(url, headers=headers)
        if resp.status_code < 500:
            return True, f"Reachable (HTTP {resp.status_code})"
        return False, f"Server error (HTTP {resp.status_code})"
    except httpx.RequestError as exc:
        return False, f"Connection failed: {exc.__class__.__name__}"
