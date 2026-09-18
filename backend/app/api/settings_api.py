import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import SUPPORTED_LANGUAGES, SUPPORTED_WHISPER_MODELS, get_settings
from app.database import get_db
from app.models.entities import AppSetting, RemoteProvider
from app.schemas import RemoteProviderCreate, RemoteProviderOut, TestConnectionResult
from app.services.transcription.remote_provider import test_connection

router = APIRouter(prefix="/api/settings", tags=["settings"])
settings = get_settings()

DEFAULT_APP_SETTINGS = {
    "general": {
        "app_name": settings.app_name,
        "default_analysis_language": settings.default_analysis_language,
    },
    "transcription": {
        "default_provider": settings.default_transcription_provider,
        "local_model": settings.local_whisper_model,
        "compute_type": settings.local_whisper_compute_type,
        "cpu_threads": settings.local_whisper_cpu_threads,
        "max_concurrent_jobs": settings.max_concurrent_jobs,
    },
    "languages": {
        "enabled": list(SUPPORTED_LANGUAGES.keys()),
        "auto_detect_default": False,
    },
    "diarization": {
        "enabled": settings.diarization_enabled,
    },
    "llm": {
        "provider": settings.llm_provider,
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "timeout_seconds": settings.llm_timeout_seconds,
        "analysis_language": settings.default_analysis_language,
    },
}


def _mask(token: str | None) -> str:
    if not token:
        return ""
    if len(token) <= 4:
        return "*" * len(token)
    return token[:2] + "*" * (len(token) - 4) + token[-2:]


@router.get("")
def get_all_settings(db: Session = Depends(get_db)):
    out = {}
    for key, default_value in DEFAULT_APP_SETTINGS.items():
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        out[key] = row.value if row else default_value
    return out


@router.put("/{section}")
def update_settings(section: str, body: dict, db: Session = Depends(get_db)):
    if section not in DEFAULT_APP_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Unknown settings section '{section}'")
    row = db.query(AppSetting).filter(AppSetting.key == section).first()
    if not row:
        row = AppSetting(key=section, value=body)
        db.add(row)
    else:
        merged = {**row.value, **body}
        row.value = merged
    db.commit()
    return row.value


# --- Remote transcription providers ---


@router.get("/remote-providers", response_model=list[RemoteProviderOut])
def list_remote_providers(db: Session = Depends(get_db)):
    rows = db.query(RemoteProvider).all()
    return [
        RemoteProviderOut(
            id=r.id,
            name=r.name,
            base_url=r.base_url,
            endpoint_path=r.endpoint_path,
            model=r.model,
            auth_method=r.auth_method,
            connect_timeout_seconds=r.connect_timeout_seconds,
            read_timeout_seconds=r.read_timeout_seconds,
            total_timeout_seconds=r.total_timeout_seconds,
            tls_verify=r.tls_verify,
            api_token_masked=_mask(r.api_token),
        )
        for r in rows
    ]


@router.post("/remote-providers", response_model=RemoteProviderOut)
def create_remote_provider(body: RemoteProviderCreate, db: Session = Depends(get_db)):
    if db.query(RemoteProvider).filter(RemoteProvider.name == body.name).first():
        raise HTTPException(status_code=400, detail="A provider with this name already exists")
    row = RemoteProvider(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return RemoteProviderOut(
        id=row.id,
        name=row.name,
        base_url=row.base_url,
        endpoint_path=row.endpoint_path,
        model=row.model,
        auth_method=row.auth_method,
        connect_timeout_seconds=row.connect_timeout_seconds,
        read_timeout_seconds=row.read_timeout_seconds,
        total_timeout_seconds=row.total_timeout_seconds,
        tls_verify=row.tls_verify,
        api_token_masked=_mask(row.api_token),
    )


@router.delete("/remote-providers/{provider_id}")
def delete_remote_provider(provider_id: str, db: Session = Depends(get_db)):
    row = db.query(RemoteProvider).filter(RemoteProvider.id == provider_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.post("/remote-providers/{provider_id}/test", response_model=TestConnectionResult)
def test_remote_provider(provider_id: str, db: Session = Depends(get_db)):
    row = db.query(RemoteProvider).filter(RemoteProvider.id == provider_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    ok, message = test_connection(row)
    return TestConnectionResult(success=ok, message=message)


# --- Local model management ---


class ModelInfo(BaseModel):
    name: str
    installed: bool
    is_current_default: bool


@router.get("/models", response_model=list[ModelInfo])
def list_models():
    installed = set()
    if settings.models_dir.exists():
        for p in settings.models_dir.iterdir():
            if p.is_dir():
                installed.add(p.name)
    out = []
    for m in SUPPORTED_WHISPER_MODELS:
        matched = any(m in name for name in installed)
        out.append(ModelInfo(name=m, installed=matched, is_current_default=(m == settings.local_whisper_model)))
    return out


@router.post("/models/{model_name}/download")
def download_model(model_name: str):
    if model_name not in SUPPORTED_WHISPER_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model '{model_name}'")
    from app.services.transcription.local_provider import _load_model

    try:
        _load_model(model_name, settings.local_whisper_device, settings.local_whisper_compute_type, 0)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Model download failed: {exc}") from exc
    return {"downloaded": model_name}


@router.delete("/models/{model_name}")
def delete_model(model_name: str):
    if not settings.models_dir.exists():
        raise HTTPException(status_code=404, detail="No models directory")
    removed = False
    for p in settings.models_dir.iterdir():
        if p.is_dir() and model_name in p.name:
            shutil.rmtree(p)
            removed = True
    if not removed:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' is not installed")
    return {"deleted": model_name}
