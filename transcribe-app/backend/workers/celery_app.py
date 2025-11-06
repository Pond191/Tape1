from celery import Celery
from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "transcribe",
    broker=settings.broker_url,
    backend=settings.backend_url,
    include=["backend.workers.tasks"],  # สำคัญ!
)

celery_app.conf.task_routes = {
    "backend.workers.tasks.*": {"queue": "transcribe"},
}

QUEUE_NAME = "transcribe"
