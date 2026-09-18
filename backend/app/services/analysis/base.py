from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ActionItemResult:
    action: str
    owner: str = "Not specified"
    due_date: str = "Not specified"
    priority: str = "Not specified"
    timestamp: str | None = None
    source_segment_ids: list[int] = field(default_factory=list)
    context: str | None = None


@dataclass
class AnalysisResult:
    summary: str = ""
    key_discussion_points: list[str] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    action_items: list[ActionItemResult] = field(default_factory=list)
    open_issues: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    important_dates: list[dict] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)
    provider: str = ""
    model: str = ""


class MeetingAnalyzer(ABC):
    """All LLM-backed analysis goes through this interface. Analysis is fully
    independent of transcription — any provider implementing this can be swapped
    in without touching the transcription pipeline."""

    name: str = "base"

    @abstractmethod
    def analyze(self, segments: list[dict], analysis_language: str) -> AnalysisResult:
        raise NotImplementedError


class AnalysisError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable
