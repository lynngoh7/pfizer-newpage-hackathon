"""Session-only allowlist for folders and files the assistant may read."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import audit

DENY_PARTS = {".ssh", ".env", "Keychains", ".gnupg"} #banned file types
allowed_folders: set[Path] = set() #paths stored in a set

# Revoke hooks (brief §6 "No copies"; task 4b): taking a folder away must drop
# everything read from it at once, not on next launch. Modules that hold note
# data register here, e.g. db.py at import time:
#     permissions.on_revoke("index", drop_chunks_under)  # fn(path) -> count
# Each fn gets the resolved path and drops entries equal to it or inside it.
_revoke_hooks: dict[str, Callable[[Path], int | None]] = {}


def on_revoke(name: str, drop: Callable[[Path], int | None]) -> None:
    _revoke_hooks[name] = drop


def _resolve_allowed_location(path: str) -> Path:
    """resolves given locations by checking if they are valid"""
    real = Path(path).resolve(strict=True)
    if any(part in DENY_PARTS for part in real.parts): #if any files in real contain a restricted file (ssh)
        raise PermissionError("Blocked location") #stop the process
    if not real.is_dir() and not real.is_file():
        raise PermissionError("Only files and folders can be allowed")
    return real


def grant_path(path: str, outcome: str = "ok") -> Path:
    """Grant access to an existing file or folder for this backend session.
    Audit (§6): logs folder_added, or blocked when the denylist refuses it.
    Paths only, never content."""
    try:
        real = _resolve_allowed_location(path)
    except PermissionError as error:
        audit.record("blocked", path=path, outcome=str(error))
        raise
    allowed_folders.add(real)
    audit.record("folder_added", path=str(real), outcome=outcome)
    return real


def revoke_path(path: str, outcome: str = "ok") -> Path:
    """Revoke one previously granted file or folder. Logged only if it was granted."""
    real = Path(path).resolve()
    if real in allowed_folders:
        allowed_folders.discard(real)
        dropped = {name: drop(real) for name, drop in _revoke_hooks.items()}
        # Counts only, e.g. "index: 42 dropped", never what was dropped.
        detail = ", ".join(f"{k}: {v} dropped" for k, v in dropped.items() if v is not None)
        audit.record("folder_removed", path=str(real), outcome=f"{outcome}; {detail}" if detail else outcome)
    return real


def list_allowed_paths() -> list[Path]:
    return sorted(allowed_folders, key=lambda path: str(path).casefold())


def resolve_and_check(path: str) -> Path:
    """Resolve symlinks and enforce the denylist and session allowlist.
    Given a Path should return resolved path if the path is allowed
    Use when reading a file!"""
    real = Path(path).resolve(strict=True)
    if any(part in DENY_PARTS for part in real.parts):
        raise PermissionError("Blocked location")
    if not any(
        real == allowed or (allowed.is_dir() and real.is_relative_to(allowed))
        for allowed in allowed_folders
    ):
        raise PermissionError("Outside allowed folders")
    return real
