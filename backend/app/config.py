"""Runtime settings, all from environment variables set by the Tauri launcher.

Hard rules enforced here (not configurable):
  * HOST is always 127.0.0.1.
  * A session token is mandatory. Without one the server refuses to start.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

HOST = "127.0.0.1"  # never configurable


@dataclass(frozen=True)
class Settings:
    port: int
    session_token: str
    read_only: bool = True
    # True only during development (NOTES_DEV=1). Lets the browser-only dev
    # server (Vite on port 1420) call the backend. Packaged builds never set it,
    # so a packaged app only ever answers the desktop window.
    dev: bool = False


def load_settings() -> Settings:
    token = os.environ.get("NOTES_SESSION_TOKEN", "").strip()
    # 32+ chars = too long to guess. The launcher makes a fresh one every run.
    if len(token) < 32:
        print(
            "refusing to start: NOTES_SESSION_TOKEN missing or too short (need >= 32 chars)",
            file=sys.stderr,
        )
        sys.exit(2)
    port = int(os.environ.get("NOTES_PORT", "8765"))  # the launcher picks a free port
    dev = os.environ.get("NOTES_DEV", "") == "1"
    return Settings(port=port, session_token=token, dev=dev)
