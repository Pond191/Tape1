#!/bin/sh
set -e

mkdir -p /data/uploads /data/jobs

if [ "$(id -u)" = "0" ]; then
  chown -R app:app /data 2>/dev/null || true
  exec gosu app "$@"
fi

exec "$@"
