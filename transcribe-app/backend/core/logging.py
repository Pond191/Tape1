import logging
import os
from logging.config import dictConfig
from pathlib import Path
from typing import Dict, List


def _prepare_file_handler(log_dir: str | None) -> Dict[str, object] | None:
    if not log_dir:
        return None
    try:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        return None
    log_file = path / "backend.log"
    return {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "structured",
        "filename": str(log_file),
        "maxBytes": 5 * 1024 * 1024,
        "backupCount": 5,
        "encoding": "utf-8",
    }


def configure_logging(level: str = "INFO", log_dir: str | None = None) -> None:
    log_directory = log_dir or os.getenv("TRANSCRIBE_LOG_DIR")
    handlers: Dict[str, Dict[str, object]] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        }
    }

    file_handler = _prepare_file_handler(log_directory)
    if file_handler:
        handlers["file"] = file_handler

    handler_names: List[str] = list(handlers.keys())

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structured": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": handlers,
            "root": {
                "handlers": handler_names,
                "level": level,
            },
        }
    )

    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)


logger = logging.getLogger("transcribe")
