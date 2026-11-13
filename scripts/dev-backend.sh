#!/bin/sh
# Run the FastAPI sidecar alone for development.
# Usage: NOTES_SESSION_TOKEN=<token> NOTES_PORT=8765 sh scripts/dev-backend.sh
set -e
cd "$(dirname "$0")/../backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -e ".[dev]"
fi
: "${NOTES_SESSION_TOKEN:?set NOTES_SESSION_TOKEN (>= 32 chars)}"
exec .venv/bin/python -m app.main
