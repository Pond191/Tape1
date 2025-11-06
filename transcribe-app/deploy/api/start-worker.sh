#!/usr/bin/env bash
set -euo pipefail

mkdir -p /data/uploads /data/jobs /data/logs || true
export PYTHONPATH=/app

# Concurrency can be tuned; keep default 4–12
exec celery -A backend.workers.celery_app.celery_app worker \
  --loglevel=INFO \
  --hostname=worker@%h \
  --queues=transcribe
