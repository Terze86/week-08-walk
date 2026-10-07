#!/usr/bin/env bash
# One-time setup when the dev container / Codespace is created.
set -euo pipefail
cd "$(dirname "$0")/../lims"

echo "==> Installing backend"
"${PYTHON:-python}" -m venv backend/.venv
backend/.venv/bin/pip install --quiet --upgrade pip
backend/.venv/bin/pip install --quiet -e "backend[dev]"

echo "==> Installing frontend"
(cd frontend && npm ci --no-audit --no-fund)

echo "==> Setup complete. start.sh launches the app."
