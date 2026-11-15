#!/bin/sh
# Browser-only dev loop (no Rust needed): one shared token for backend + Vite.
# With Rust installed, prefer `npm run tauri dev`, which does this automatically.
set -e
cd "$(dirname "$0")/.."
TOKEN=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
PORT=${NOTES_PORT:-8765}
export NOTES_SESSION_TOKEN="$TOKEN" NOTES_PORT="$PORT" NOTES_DEV=1
sh scripts/dev-backend.sh &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT INT TERM
VITE_BACKEND_PORT="$PORT" VITE_SESSION_TOKEN="$TOKEN" npx vite
