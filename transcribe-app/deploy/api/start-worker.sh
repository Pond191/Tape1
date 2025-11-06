#!/usr/bin/env sh
set -e
exec celery -A backend.workers.celery_app.celery_app worker \
  -Q "${CELERY_QUEUE:-transcribe}" --loglevel=INFO
