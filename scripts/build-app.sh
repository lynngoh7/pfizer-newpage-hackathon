#!/bin/sh
# Build the desktop app and install it into /Applications so it shows up in
# Launchpad, Spotlight and Finder like any other app.
# Usage: sh scripts/build-app.sh            (build + install)
#        sh scripts/build-app.sh --install  (install the last build only)
set -e
cd "$(dirname "$0")/.."
APP="Local Notes Assistant.app"
SRC="src-tauri/target/release/bundle/macos/$APP"
if [ "$1" != "--install" ]; then
  sh scripts/build-sidecar.sh
  npm run tauri build
fi
[ -d "$SRC" ] || { echo "no build at $SRC"; exit 1; }
# Quit a running copy first so the replace doesn't leave a stale backend.
osascript -e "quit app \"Local Notes Assistant\"" 2>/dev/null || true
rm -rf "/Applications/$APP"
ditto "$SRC" "/Applications/$APP"
# Unsigned build: drop the download quarantine flag if present.
xattr -dr com.apple.quarantine "/Applications/$APP" 2>/dev/null || true
echo "installed /Applications/$APP"
