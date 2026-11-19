#!/bin/sh
# Privacy guard (brief §6 "No network"): fail if app code contains a URL
# that points anywhere other than this machine. Allowed hosts: 127.0.0.1,
# localhost and tauri.localhost (the Tauri window's own origin).
# Run from the repo root: sh scripts/privacy-guard.sh
set -eu

# -o prints each URL on its own line, so one allowed URL cannot hide
# a remote one on the same line.
found=$(grep -rnoIE --exclude-dir=__pycache__ --exclude-dir=node_modules 'https?://[^"'"'"'`[:space:])]*' src backend/app \
  | grep -vE 'https?://(127\.0\.0\.1|localhost|tauri\.localhost)([:/]|$)' || true)

if [ -n "$found" ]; then
  echo "Outbound URL found in app code (only localhost is allowed):"
  echo "$found"
  exit 1
fi
echo "Privacy guard passed: no outbound URLs in src/ or backend/app/."
