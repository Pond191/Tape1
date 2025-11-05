#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

# ชื่อ queue มาจาก env CELERY_QUEUE (docker-compose ตั้งไว้เป็น "transcribe")
exec celery -A backend.workers.celery_app.celery_app worker -l info -Q "${CELERY_QUEUE:-transcribe}"
