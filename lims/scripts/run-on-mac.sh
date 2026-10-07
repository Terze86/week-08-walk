#!/usr/bin/env bash
# Install (first run only) and start the DNA LIMS on a Mac, then open it in
# the browser. Safe to run again at any time; it restarts the app.
#
#   bash lims/scripts/run-on-mac.sh
#
# Needs Homebrew (https://brew.sh). Uses Python 3.12, Node 22 and PostgreSQL 16
# from Homebrew, and a local database "lims" with demo data only.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

if ! command -v brew > /dev/null; then
  echo "Homebrew is required. Install it from https://brew.sh, then run this again." >&2
  exit 1
fi

for formula in python@3.12 node@22 postgresql@16; do
  if ! brew list --versions "$formula" > /dev/null; then
    echo "==> Installing $formula"
    brew install "$formula"
  fi
done
PATH="$(brew --prefix python@3.12)/libexec/bin:$(brew --prefix node@22)/bin:$(brew --prefix postgresql@16)/bin:$PATH"
export PATH

echo "==> Starting PostgreSQL"
brew services start postgresql@16 > /dev/null || true
for _ in $(seq 1 30); do
  pg_isready -q -h localhost && break
  sleep 1
done
pg_isready -q -h localhost || { echo "PostgreSQL did not start" >&2; exit 1; }

if [ "$(psql -h localhost -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'lims'")" != "1" ]; then
  echo "==> Creating database user 'lims'"
  psql -h localhost -d postgres -qc "CREATE ROLE lims LOGIN PASSWORD 'lims' CREATEDB"
fi
if [ "$(psql -h localhost -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'lims'")" != "1" ]; then
  echo "==> Creating database 'lims'"
  createdb -h localhost -O lims lims
fi

if [ ! -x "$REPO/lims/backend/.venv/bin/python" ] || [ ! -d "$REPO/lims/frontend/node_modules" ]; then
  PYTHON=python bash "$REPO/.devcontainer/setup.sh"
fi

LIMS_DATABASE_URL="postgresql+psycopg://lims:lims@localhost:5432/lims" \
  bash "$REPO/.devcontainer/start.sh"

echo
echo "Open http://localhost:5173 and sign in as admin1, cs1, slo1, dlo1, rev1 or codis1."
echo "To stop: bash lims/scripts/stop.sh"
open "http://localhost:5173" 2> /dev/null || true
