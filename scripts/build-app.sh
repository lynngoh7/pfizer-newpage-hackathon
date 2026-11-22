#!/bin/sh
# Build the desktop app and install it so it shows in the OS app list.
#   macOS:   copies the .app into /Applications (Launchpad, Spotlight)
#   Windows: runs the setup .exe (Start menu). Use Git Bash.
#   Linux:   installs the .deb or .rpm (app menu); needs sudo
# Usage: sh scripts/build-app.sh            (build + install)
#        sh scripts/build-app.sh --install  (install the last build only)
set -e
cd "$(dirname "$0")/.."
NAME="Haystack"
B=src-tauri/target/release/bundle
if [ "$1" != "--install" ]; then
  sh scripts/build-sidecar.sh
  npm run tauri build
fi
case "$(uname -s)" in
  Darwin)
    SRC="$B/macos/$NAME.app"
    [ -d "$SRC" ] || { echo "no build at $SRC"; exit 1; }
    # Quit a running copy first so the replace doesn't leave a stale backend.
    osascript -e "quit app \"$NAME\"" 2>/dev/null || true
    rm -rf "/Applications/$NAME.app"
    ditto "$SRC" "/Applications/$NAME.app"
    # Unsigned build: drop the quarantine flag if present.
    xattr -dr com.apple.quarantine "/Applications/$NAME.app" 2>/dev/null || true
    echo "installed /Applications/$NAME.app" ;;
  MINGW*|MSYS*|CYGWIN*)
    SETUP=$(ls "$B"/nsis/*-setup.exe 2>/dev/null | head -1)
    [ -n "$SETUP" ] || { echo "no installer in $B/nsis"; exit 1; }
    # /S = silent install for the current user; adds a Start menu entry.
    "$SETUP" /S
    echo "installed $NAME (Start menu)" ;;
  Linux)
    DEB=$(ls "$B"/deb/*.deb 2>/dev/null | head -1)
    RPM=$(ls "$B"/rpm/*.rpm 2>/dev/null | head -1)
    if command -v apt-get >/dev/null && [ -n "$DEB" ]; then
      sudo apt-get install -y "./$DEB"
    elif command -v dnf >/dev/null && [ -n "$RPM" ]; then
      sudo dnf install -y "$RPM"
    else
      echo "no .deb/.rpm for this distro; run the AppImage in $B/appimage instead"; exit 1
    fi
    echo "installed $NAME (app menu)" ;;
  *) echo "unsupported OS: $(uname -s)"; exit 1 ;;
esac
