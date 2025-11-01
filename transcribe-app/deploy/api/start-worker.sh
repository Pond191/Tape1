#!/usr/bin/env sh
set -e

mkdir -p /data/uploads /data/jobs
chown -R 1000:1000 /data 2>/dev/null || true

python - <<'PY'
from backend.db.session import init_db

try:
    init_db()
except Exception as exc:
    print(f"Database initialisation failed: {exc}")
PY

exec gosu app python -m backend.workers.run_worker
