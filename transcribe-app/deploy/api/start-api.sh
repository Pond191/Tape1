#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

# รอ DB/Redis แป๊บ (ไม่ต้องรอถ้าดีอยู่แล้ว)
# sleep 2

exec uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
