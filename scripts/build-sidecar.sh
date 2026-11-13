#!/bin/sh
# Package the backend with PyInstaller and drop it where the Tauri app looks
# for it (next to the executable at runtime; src-tauri/binaries for bundling).
set -e
cd "$(dirname "$0")/../backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -e ".[package]"
.venv/bin/pyinstaller --clean --noconfirm notes-backend.spec
mkdir -p ../src-tauri/binaries
cp dist/notes-backend ../src-tauri/binaries/notes-backend
echo "sidecar at src-tauri/binaries/notes-backend"
