import platform
import shutil

from fastapi import APIRouter

from app.config import SUPPORTED_WHISPER_MODELS, get_settings
from app.schemas import SystemStatusOut
from app.services.media import MediaToolError, find_ffmpeg, find_ffprobe, get_tool_version

router = APIRouter(prefix="/api/system", tags=["system"])
settings = get_settings()

APP_VERSION = "0.1.0"


@router.get("/status", response_model=SystemStatusOut)
def system_status():
    try:
        ffmpeg_version = get_tool_version(find_ffmpeg())
    except MediaToolError:
        ffmpeg_version = None
    try:
        ffprobe_version = get_tool_version(find_ffprobe())
    except MediaToolError:
        ffprobe_version = None

    ram_total_gb = ram_available_gb = 0.0
    try:
        import psutil

        vm = psutil.virtual_memory()
        ram_total_gb = round(vm.total / (1024**3), 2)
        ram_available_gb = round(vm.available / (1024**3), 2)
    except ImportError:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        total_kb = int([l for l in meminfo.splitlines() if l.startswith("MemTotal")][0].split()[1])
        avail_kb = int([l for l in meminfo.splitlines() if l.startswith("MemAvailable")][0].split()[1])
        ram_total_gb = round(total_kb / (1024**2), 2)
        ram_available_gb = round(avail_kb / (1024**2), 2)

    usage = shutil.disk_usage(settings.data_path if settings.data_path.exists() else ".")

    installed_models = []
    if settings.models_dir.exists():
        for m in SUPPORTED_WHISPER_MODELS:
            if any(m in p.name for p in settings.models_dir.iterdir() if p.is_dir()):
                installed_models.append(m)

    return SystemStatusOut(
        meetsage_version=APP_VERSION,
        python_version=platform.python_version(),
        ffmpeg_version=ffmpeg_version,
        ffprobe_version=ffprobe_version,
        cpu_count=__import__("os").cpu_count() or 1,
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
        disk_total_gb=round(usage.total / (1024**3), 2),
        disk_free_gb=round(usage.free / (1024**3), 2),
        installed_models=installed_models,
    )


@router.get("/health")
def health():
    return {"status": "ok"}
