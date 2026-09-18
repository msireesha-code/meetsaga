import logging
import re
import sys

_REDACT_PATTERNS = [
    re.compile(r"(Authorization\s*:\s*Bearer\s+)([^\s\"']+)", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[=:]\s*)([^\s\"']+)", re.IGNORECASE),
    re.compile(r"(api[_-]?token\s*[=:]\s*)([^\s\"']+)", re.IGNORECASE),
    re.compile(r"(hf_[A-Za-z0-9]{10,})"),
]


class RedactingFilter(logging.Filter):
    """Defense-in-depth: strips anything that looks like a bearer token, API key,
    or Hugging Face token out of log records before they are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        redacted = msg
        for pattern in _REDACT_PATTERNS:
            redacted = pattern.sub(lambda m: (m.group(1) + "***REDACTED***") if m.lastindex and m.lastindex >= 2 else "***REDACTED***", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(fmt="%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger("meetsage").setLevel(level)
