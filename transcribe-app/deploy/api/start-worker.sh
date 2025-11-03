#!/usr/bin/env sh
set -e

mkdir -p /data/uploads /data/jobs
chown -R 1000:1000 /data 2>/dev/null || true

python - <<'PY'
from backend.db.session import init_db

init_db()
PY

exec gosu app celery -A backend.workers.celery_app worker -l info -Q transcribe,celery
