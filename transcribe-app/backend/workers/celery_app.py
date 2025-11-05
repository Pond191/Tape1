from __future__ import annotations
import os
from celery import Celery
from ..core.config import get_settings

settings = get_settings()

BROKER_URL = os.getenv("CELERY_BROKER_URL", settings.broker_url)
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", settings.backend_url)
QUEUE_NAME = os.getenv("CELERY_QUEUE", "transcribe")

celery_app = Celery("transcribe")
celery_app.conf.update(
    broker_url=BROKER_URL,
    result_backend=BACKEND_URL,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue=QUEUE_NAME,
)
