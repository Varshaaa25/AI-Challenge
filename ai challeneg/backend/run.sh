#!/usr/bin/env bash
# Simple helper to create venv, install deps, and run the FastAPI app
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
fi

echo "Activating virtualenv..."
source .venv/bin/activate

echo "Installing dependencies (pip will skip already-installed)..."
pip install -r requirements.txt

echo "Starting uvicorn via python -m uvicorn..."
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
