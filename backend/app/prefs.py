"""Saved preferences: the folder list and settings, and nothing else.

One Rule ("no copies", brief §1a): this file may hold folder/file *paths* and
setting values only. Never note text, snippets, index data, queries or
answers. SAVED_SETTINGS is an allowlist: unknown keys are dropped on load and
on save, so nothing else can sneak in.

File: <app data dir>/prefs.json (NOTES_PREFS_DIR overrides it, for tests).
The Privacy page shows this file and its contents; "Forget everything"
deletes it.

Called by: main.py (restore on launch), api.py (folder add/remove, settings).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import permissions, session

APP_ID = "local.notes.assistant"  # same folder name trust.py checks

# setting name -> (type, max length). Allowlist: anything else is never saved.
SAVED_SETTINGS = {"answer_model": (str, 100)}


def path() -> Path:
    override = os.environ.get("NOTES_PREFS_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_ID
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_ID
    else:
        base = Path.home() / ".config" / APP_ID
    return base / "prefs.json"


def _clean_settings(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, (kind, max_len) in SAVED_SETTINGS.items():
        value = raw.get(key)
        if isinstance(value, kind) and len(value) <= max_len:
            out[key] = value
    return out


def load() -> dict:
    """{"folders": [...], "settings": {...}}. Missing or broken file = empty."""
    try:
        raw = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"folders": [], "settings": {}}
    folders = raw.get("folders") if isinstance(raw, dict) else None
    return {
        "folders": [f for f in folders if isinstance(f, str)] if isinstance(folders, list) else [],
        "settings": _clean_settings(raw.get("settings") if isinstance(raw, dict) else None),
    }


def _write(data: dict) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)  # atomic: a crash never leaves a half-written file


def save_folders() -> None:
    data = load()
    data["folders"] = [str(f) for f in permissions.list_allowed_paths()]
    _write(data)


def save_settings(new: dict) -> dict:
    data = load()
    data["settings"] = {**data["settings"], **_clean_settings(new)}
    _write(data)
    return data["settings"]


def restore_folders() -> list[str]:
    """Re-grant saved folders on launch. Each goes through the same checks as a
    new grant; ones that are gone or now blocked are dropped and returned."""
    dropped = []
    for folder in load()["folders"]:
        try:
            permissions.grant_path(folder)
        except (OSError, PermissionError):
            dropped.append(folder)
    if dropped:
        save_folders()
    return dropped


def forget() -> int:
    """Forget everything: drop folder grants from memory and delete the file."""
    count = len(permissions.allowed_folders)
    permissions.allowed_folders.clear()
    try:
        path().unlink()
    except FileNotFoundError:
        pass
    return count


session.on_forget("folders", forget)
