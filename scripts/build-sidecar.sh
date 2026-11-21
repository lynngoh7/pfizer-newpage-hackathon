#!/bin/sh
# Package the backend with PyInstaller and drop it where the Tauri app looks
# for it (next to the executable at runtime; src-tauri/binaries for bundling).
set -e
cd "$(dirname "$0")/../backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -e ".[package]"
.venv/bin/pyinstaller --clean --noconfirm notes-backend.spec
mkdir -p ../src-tauri/binaries
# Tauri bundles externalBin files named with the target triple, and installs
# them next to the app executable as plain `notes-backend` (where sidecar.rs looks).
TRIPLE=$(rustc -vV | sed -n 's/^host: //p')
rm -f ../src-tauri/binaries/notes-backend
cp dist/notes-backend "../src-tauri/binaries/notes-backend-$TRIPLE"
echo "sidecar at src-tauri/binaries/notes-backend-$TRIPLE"
