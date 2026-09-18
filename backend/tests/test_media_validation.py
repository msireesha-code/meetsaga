import pytest

from app.services.media.validation import (
    UploadValidationError,
    classify_media_type,
    sanitize_filename,
    validate_size,
)


def test_sanitize_filename_strips_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"


def test_sanitize_filename_strips_unsafe_characters():
    result = sanitize_filename("my meeting!@#.wav")
    assert result.endswith(".wav")
    assert " " not in result
    assert "!" not in result


def test_sanitize_filename_rejects_empty():
    with pytest.raises(UploadValidationError):
        sanitize_filename("")


def test_sanitize_filename_rejects_dot_dot():
    with pytest.raises(UploadValidationError):
        sanitize_filename("..")


def test_classify_media_type_audio():
    assert classify_media_type("recording.mp3") == "audio"
    assert classify_media_type("recording.m4a") == "audio"


def test_classify_media_type_video():
    assert classify_media_type("recording.mp4") == "video"


def test_classify_media_type_rejects_unsupported_extension():
    with pytest.raises(UploadValidationError):
        classify_media_type("script.sh")


def test_validate_size_rejects_oversized():
    with pytest.raises(UploadValidationError):
        validate_size(999_999_999, max_mb=10)


def test_validate_size_rejects_empty():
    with pytest.raises(UploadValidationError):
        validate_size(0, max_mb=10)


def test_validate_size_accepts_within_limit():
    validate_size(1024, max_mb=10)  # must not raise
