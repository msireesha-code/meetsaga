import re
from pathlib import Path

from app.config import SUPPORTED_AUDIO_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class UploadValidationError(ValueError):
    pass


def sanitize_filename(filename: str) -> str:
    """Strip any path components and unsafe characters. Never trust the client-
    supplied filename for filesystem paths — only for display."""
    name = Path(filename).name  # drops any directory traversal component
    name = _SAFE_NAME.sub("_", name)
    if not name or name in {".", ".."}:
        raise UploadValidationError("Invalid filename")
    return name[:255]


def classify_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in SUPPORTED_AUDIO_EXTENSIONS:
        return "audio"
    if ext in SUPPORTED_VIDEO_EXTENSIONS:
        return "video"
    allowed = sorted(SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS)
    raise UploadValidationError(f"Unsupported file extension '{ext}'. Allowed: {', '.join(allowed)}")


def validate_size(size_bytes: int, max_mb: int) -> None:
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise UploadValidationError(f"File exceeds maximum upload size of {max_mb}MB")
    if size_bytes <= 0:
        raise UploadValidationError("Uploaded file is empty")
