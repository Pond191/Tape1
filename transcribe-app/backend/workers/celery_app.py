"""Celery application factory shared between the API and worker containers."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

try:  # Celery is optional for unit tests
    from celery import Celery  # type: ignore
    from kombu import Queue
except Exception:  # pragma: no cover - allow importing without Celery installed
    Celery = None  # type: ignore
    Queue = None  # type: ignore

from backend.core.config import get_settings


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache()
def _queue_name() -> str:
    return os.getenv("CELERY_QUEUE", "transcribe")


def _broker_url() -> str:
    settings = get_settings()
    return os.getenv("CELERY_BROKER_URL", settings.broker_url)


def _backend_url() -> str:
    settings = get_settings()
    return os.getenv("CELERY_RESULT_BACKEND", settings.backend_url)


@lru_cache()
def create_celery_app() -> Optional[Celery]:
    if Celery is None or Queue is None:
        return None

    broker_url = _broker_url()
    backend_url = _backend_url()
    queue_name = _queue_name()

    app = Celery(
        "transcribe",
        broker=broker_url,
        backend=backend_url,
        include=["backend.workers.tasks"],
    )

    # Ensure both API and worker share the same queue configuration.
    app.conf.update(
        broker_connection_retry_on_startup=True,
        task_default_queue=queue_name,
        task_default_exchange=queue_name,
        task_default_routing_key=queue_name,
        task_queues=(
            Queue(queue_name, routing_key=queue_name),
            Queue("celery", routing_key="celery"),
        ),
        task_always_eager=_env_bool("CELERY_EAGER", False),
        worker_prefetch_multiplier=int(os.getenv("CELERY_PREFETCH", "1")),
    )

    app.set_default()

    return app


celery_app = create_celery_app()
QUEUE_NAME = _queue_name()

__all__ = ["celery_app", "QUEUE_NAME", "create_celery_app"]
