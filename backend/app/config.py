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


def load_settings() -> Settings:
    token = os.environ.get("NOTES_SESSION_TOKEN", "").strip()
    if len(token) < 32:
        print(
            "refusing to start: NOTES_SESSION_TOKEN missing or too short (need >= 32 chars)",
            file=sys.stderr,
        )
        sys.exit(2)
    port = int(os.environ.get("NOTES_PORT", "8765"))
    return Settings(port=port, session_token=token)
