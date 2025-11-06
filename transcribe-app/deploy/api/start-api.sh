#!/usr/bin/env bash
set -euo pipefail

# Ensure storage exists (in case of fresh container)
mkdir -p /data/uploads /data/jobs /data/logs || true

export PYTHONPATH=/app

# Run API
exec uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers
