#!/usr/bin/env bash
# Starts the LIMS API and web app in the background. Safe to run again:
# it restarts both. Logs: /tmp/lims-api.log and /tmp/lims-web.log
set -euo pipefail
cd "$(dirname "$0")/../lims"
export LIMS_DATABASE_URL="${LIMS_DATABASE_URL:-postgresql+psycopg://lims:lims@db:5432/lims}"

echo "==> Waiting for the database"
db_ready=""
for _ in $(seq 1 60); do
  if (cd backend && .venv/bin/python -c "
import sys, sqlalchemy as sa
from app.core.config import get_settings
try:
    sa.create_engine(get_settings().database_url).connect().close()
except Exception:
    sys.exit(1)
" 2>/dev/null); then db_ready=1; break; fi
  sleep 2
done
if [ -z "$db_ready" ]; then
  echo "!! Could not reach the database at $LIMS_DATABASE_URL" >&2
  exit 1
fi

echo "==> Updating database and demo data"
(cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m app.seed)

echo "==> Starting API (port 8000) and web app (port 5173)"
# Stop servers left by a previous run (tracked by PID file, never by name).
for name in api web; do
  if [ -f "/tmp/lims-$name.pid" ]; then
    kill -- "-$(cat "/tmp/lims-$name.pid")" 2>/dev/null || true
    rm -f "/tmp/lims-$name.pid"
  fi
done
sleep 1
# Each server runs detached in its own process group with its own log, so this
# script (and the Codespaces start step) finishes instead of waiting on them.
# Python's os.setsid is used because macOS has no `setsid` command.
detach=(backend/.venv/bin/python -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])')
detach[0]="$PWD/${detach[0]}"
(cd backend && exec nohup "${detach[@]}" .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) \
  > /tmp/lims-api.log 2>&1 < /dev/null &
echo $! > /tmp/lims-api.pid
(cd frontend && exec nohup "${detach[@]}" npx vite --host 0.0.0.0 --port 5173 --strictPort) \
  > /tmp/lims-web.log 2>&1 < /dev/null &
echo $! > /tmp/lims-web.pid

for _ in $(seq 1 30); do
  if curl -fs http://localhost:5173 > /dev/null && curl -fs http://localhost:8000/health > /dev/null; then
    echo "==> DNA LIMS is running at http://localhost:5173 (in Codespaces: PORTS tab, globe next to 5173)."
    exit 0
  fi
  sleep 1
done
echo "!! The app did not start; see /tmp/lims-api.log and /tmp/lims-web.log" >&2
exit 1
