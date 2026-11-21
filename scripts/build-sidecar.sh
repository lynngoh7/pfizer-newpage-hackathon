#!/bin/sh
# Package the backend with PyInstaller and drop it where the Tauri app looks
# for it (next to the executable at runtime; src-tauri/binaries for bundling).
set -e
cd "$(dirname "$0")/../backend"
# Windows (Git Bash) has `python` and puts venv tools in Scripts/ with .exe.
PY=$(command -v python3 || command -v python)
[ -d .venv ] || "$PY" -m venv .venv
BIN=.venv/bin; EXT=
[ -d .venv/Scripts ] && { BIN=.venv/Scripts; EXT=.exe; }
"$BIN/python" -m pip install -q -e ".[package]"
"$BIN/pyinstaller" --clean --noconfirm notes-backend.spec
mkdir -p ../src-tauri/binaries
# Tauri bundles externalBin files named with the target triple, and installs
# them next to the app executable as plain `notes-backend` (where sidecar.rs looks).
# On Windows both names end in .exe.
TRIPLE=$(rustc -vV | sed -n 's/^host: //p')
[ -n "$TRIPLE" ] || { echo "rustc not found: install Rust first"; exit 1; }
rm -f ../src-tauri/binaries/notes-backend ../src-tauri/binaries/notes-backend.exe
cp "dist/notes-backend$EXT" "../src-tauri/binaries/notes-backend-$TRIPLE$EXT"
echo "sidecar at src-tauri/binaries/notes-backend-$TRIPLE$EXT"
