#!/usr/bin/env sh
set -e

mkdir -p /data/uploads /data/jobs
chown -R 1000:1000 /data 2>/dev/null || true

id || true
echo "MAX_UPLOAD_MB=${MAX_UPLOAD_MB:-unset}"

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
