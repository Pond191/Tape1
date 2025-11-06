# backend/workers/celery_app.py
from __future__ import annotations

import os
from celery import Celery

QUEUE_NAME = os.getenv("CELERY_QUEUE", "transcribe")

broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://redis:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND") or os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("transcribe", broker=broker_url, backend=result_backend)
celery_app.conf.task_default_queue = QUEUE_NAME
celery_app.autodiscover_tasks(["backend.workers"], related_name="tasks")
