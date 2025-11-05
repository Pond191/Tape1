import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes"}


@dataclass
class Settings:
    app_name: str = "DialectTranscribe"
    environment: str = "development"
    log_level: str = "INFO"
    storage_dir: str = "/data"
    log_dir: str = "/data/logs"
    max_upload_mb: int = 200
    retention_days: int = 30
    database_url: str = "postgresql+psycopg://transcribe:transcribe@db:5432/transcribe"
    broker_url: str = "redis://redis:6379/0"
    backend_url: str = "redis://redis:6379/0"
    default_model_size: str = "small"
    enable_gpu: bool = True
    vad_engine: str = "webrtc"
    diarization_engine: str = "pyannote"
    enable_redaction: bool = False
    # ✅ แก้ regex ให้ถูกต้อง
    redact_patterns: str = r"(?P<phone>0[689]\d{8})|(?P<national_id>\d{13})|(?P<account>\d{10,12})"
    asr_backend: str = "auto"
    whisper_compute_type: Optional[str] = None
    whisper_download_root: Optional[str] = None


def _build_settings_kwargs() -> Dict[str, Any]:
    database_url = (
        os.getenv("TRANSCRIBE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql+psycopg://transcribe:transcribe@db:5432/transcribe"
    )
    storage_dir = os.getenv("TRANSCRIBE_STORAGE_DIR", "/data")
    return {
        "app_name": os.getenv("TRANSCRIBE_APP_NAME", "DialectTranscribe"),
        "environment": os.getenv("TRANSCRIBE_ENVIRONMENT", "development"),
        "log_level": os.getenv("TRANSCRIBE_LOG_LEVEL", "INFO"),
        "storage_dir": storage_dir,
        "log_dir": os.getenv("TRANSCRIBE_LOG_DIR", os.path.join(storage_dir, "logs")),
        "max_upload_mb": int(os.getenv("MAX_UPLOAD_MB", "200")),
        "retention_days": int(os.getenv("TRANSCRIBE_RETENTION_DAYS", "30")),
        "database_url": database_url,
        "broker_url": os.getenv("TRANSCRIBE_BROKER_URL", "redis://redis:6379/0"),
        "backend_url": os.getenv("TRANSCRIBE_BACKEND_URL", "redis://redis:6379/0"),
        "default_model_size": os.getenv("TRANSCRIBE_DEFAULT_MODEL_SIZE", "small"),
        "enable_gpu": _get_bool("TRANSCRIBE_ENABLE_GPU", True),
        "vad_engine": os.getenv("TRANSCRIBE_VAD_ENGINE", "webrtc"),
        "diarization_engine": os.getenv("TRANSCRIBE_DIARIZATION_ENGINE", "pyannote"),
        "enable_redaction": _get_bool("TRANSCRIBE_ENABLE_REDACTION", False),
        "redact_patterns": os.getenv(
            "TRANSCRIBE_REDACT_PATTERNS",
            r"(?P<phone>0[689]\d{8})|(?P<national_id>\d{13})|(?P<account>\d{10,12})",
        ),
        "asr_backend": os.getenv("TRANSCRIBE_ASR_BACKEND", "auto"),
        "whisper_compute_type": os.getenv("TRANSCRIBE_WHISPER_COMPUTE_TYPE"),
        "whisper_download_root": os.getenv("TRANSCRIBE_WHISPER_DOWNLOAD_ROOT"),
    }


@lru_cache()
def get_settings() -> Settings:
    settings = Settings(**_build_settings_kwargs())
    os.makedirs(settings.storage_dir, exist_ok=True)
    if settings.log_dir:
        os.makedirs(settings.log_dir, exist_ok=True)
    return settings
