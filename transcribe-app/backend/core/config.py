import os
from dataclasses import dataclass
from functools import lru_cache


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes"}


@dataclass
class Settings:
    app_name: str = os.getenv("TRANSCRIBE_APP_NAME", "DialectTranscribe")
    environment: str = os.getenv("TRANSCRIBE_ENVIRONMENT", "development")
    log_level: str = os.getenv("TRANSCRIBE_LOG_LEVEL", "INFO")
    storage_dir: str = os.getenv("TRANSCRIBE_STORAGE_DIR", "/tmp/transcribe-storage")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "200"))
    retention_days: int = int(os.getenv("TRANSCRIBE_RETENTION_DAYS", "30"))
    database_url: str = os.getenv(
        "TRANSCRIBE_DATABASE_URL",
        "postgresql+psycopg2://transcribe:transcribe@db:5432/transcribe",
    )
    broker_url: str = os.getenv("TRANSCRIBE_BROKER_URL", "redis://redis:6379/0")
    backend_url: str = os.getenv("TRANSCRIBE_BACKEND_URL", "redis://redis:6379/1")
    default_model_size: str = os.getenv("TRANSCRIBE_DEFAULT_MODEL_SIZE", "small")
    enable_gpu: bool = _get_bool("TRANSCRIBE_ENABLE_GPU", True)
    vad_engine: str = os.getenv("TRANSCRIBE_VAD_ENGINE", "webrtc")
    diarization_engine: str = os.getenv("TRANSCRIBE_DIARIZATION_ENGINE", "pyannote")
    enable_redaction: bool = _get_bool("TRANSCRIBE_ENABLE_REDACTION", False)
    redact_patterns: str = os.getenv(
        "TRANSCRIBE_REDACT_PATTERNS",
        r"(?P<phone>0[689]\d{8})|(?P<national_id>\d{13})|(?P<account>\d{10,12})",
    )


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.storage_dir, exist_ok=True)
    return settings
