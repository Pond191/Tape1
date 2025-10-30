"""Utility entrypoint for starting the Celery worker safely."""
from __future__ import annotations

import os
import sys
import time
from typing import List

try:
    from celery import Celery  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Celery = None  # type: ignore

from backend.core.logging import configure_logging, logger
from backend.workers.tasks import celery_app


def _sleep_forever(message: str, delay: float = 60.0) -> None:
    """Log ``message`` once and then sleep forever."""
    logger.warning(message)
    while True:
        time.sleep(delay)


def _ensure_broker_connection(app: Celery, broker_url: str, delay: float) -> None:
    """Block until the Celery broker is reachable."""
    while True:
        try:
            with app.connection() as connection:
                connection.ensure_connection(max_retries=0)
            logger.info("Connected to Celery broker %s", broker_url)
            return
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning(
                "Celery broker %s unavailable (%s); retrying in %.0fs", broker_url, exc, delay
            )
            time.sleep(delay)


def main() -> None:
    log_level_setting = os.getenv("CELERY_LOG_LEVEL", "INFO")
    configure_logging(log_level_setting.upper())

    broker_url = os.getenv("CELERY_BROKER_URL")
    if not broker_url:
        _sleep_forever("CELERY_BROKER_URL not configured; worker idling")

    if Celery is None:
        _sleep_forever("Celery is not installed; worker idling")

    if celery_app is None:
        _sleep_forever("Celery app not initialised; worker idling")

    retry_delay = float(os.getenv("CELERY_BROKER_RETRY_DELAY", "5"))
    _ensure_broker_connection(celery_app, broker_url, retry_delay)

    argv: List[str] = [
        "worker",
        "-l",
        log_level_setting.lower(),
    ]

    queues = os.getenv("CELERY_QUEUES")
    if queues:
        argv.extend(["-Q", queues])

    try:
        celery_app.worker_main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        sys.exit(code)


if __name__ == "__main__":
    main()
