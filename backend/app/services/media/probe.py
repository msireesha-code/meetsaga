"""FFprobe/FFmpeg wrappers. Uses the system-installed ffmpeg/ffprobe (never bundles
or replaces them). All subprocess calls use argument lists, never shell=True, so
filenames cannot be interpreted as shell commands."""
import json
import shutil
import subprocess
from pathlib import Path


class MediaToolError(RuntimeError):
    pass


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise MediaToolError("ffmpeg was not found on PATH. Install it with: sudo apt install ffmpeg")
    return path


def find_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise MediaToolError("ffprobe was not found on PATH. Install it with: sudo apt install ffmpeg")
    return path


def get_tool_version(binary: str) -> str:
    result = subprocess.run([binary, "-version"], capture_output=True, text=True, timeout=10)
    first_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
    return first_line


def probe_media(path: Path) -> dict:
    """Run ffprobe and return parsed JSON metadata. Raises MediaToolError on failure
    (e.g. corrupted media, unsupported container)."""
    ffprobe = find_ffprobe()
    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as exc:
        raise MediaToolError(f"ffprobe timed out inspecting {path.name}") from exc

    if result.returncode != 0:
        raise MediaToolError(f"ffprobe failed on {path.name}: {result.stderr.strip()[:500]}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaToolError(f"ffprobe returned invalid JSON for {path.name}") from exc


def summarize_probe(raw: dict) -> dict:
    fmt = raw.get("format", {})
    streams = raw.get("streams", [])
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)

    duration = fmt.get("duration")
    duration_seconds = float(duration) if duration is not None else None

    return {
        "duration_seconds": duration_seconds,
        "mime_type": fmt.get("format_name"),
        "has_video": video_stream is not None,
        "has_audio": audio_stream is not None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "sample_rate": int(audio_stream["sample_rate"]) if audio_stream and audio_stream.get("sample_rate") else None,
        "channels": audio_stream.get("channels") if audio_stream else None,
        "video_codec": video_stream.get("codec_name") if video_stream else None,
    }


def extract_normalized_audio(source: Path, dest_wav: Path) -> None:
    """Extract/normalize audio to 16kHz mono PCM WAV for transcription.
    Never modifies or overwrites the original source file."""
    ffmpeg = find_ffmpeg()
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i", str(source),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-acodec", "pcm_s16le",
        str(dest_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        raise MediaToolError(f"ffmpeg audio extraction failed: {result.stderr.strip()[:500]}")
