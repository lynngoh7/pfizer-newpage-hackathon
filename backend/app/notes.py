"""Capture: open a note in the user's own editor, or save a brand-new note.

Rules (brief §1a, §6):
  * Read-only for existing files: this app never edits a note. "Open" hands
    the file to the default app (TextEdit, Word, ...); the user edits there.
  * The one write: create_note() writes a NEW file the user typed, on an
    explicit Save. Exclusive create ("x"), so it can never overwrite.
    It is the user's note, not an assistant copy, so the One Rule holds.
  * Path enforcement: open_file goes through permissions.resolve_and_check;
    create_note refuses denylisted folders.
  * Audit: paths and actions only, never note text.

Called by: api.py (POST /api/files/open, POST /api/notes).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from . import audit, permissions


def _launch(path: Path) -> None:
    # Argument list, never a shell string: a filename can't inject a command.
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_file(path: str) -> Path:
    """Open an allowed file in its default app. Raises PermissionError otherwise."""
    try:
        real = permissions.resolve_and_check(path)  # §6 path enforcement
    except PermissionError as error:
        audit.record("blocked", path=path, outcome=str(error))
        raise
    if not real.is_file():
        raise PermissionError("Only files can be opened")
    _launch(real)
    audit.record("open_in_editor", path=str(real))
    return real


def is_tracked(folder: Path) -> bool:
    """True if notes saved in this folder will be indexed (inside an allowed folder)."""
    return any(
        allowed.is_dir() and (folder == allowed or folder.is_relative_to(allowed))
        for allowed in permissions.allowed_folders
    )


def _safe_name(title: str) -> str:
    """Turn a note title into a filename that is valid on Mac, Windows and Linux."""
    # Replace characters that are illegal in filenames on some OS with a space:
    #   \ /          path separators (would create subfolders / escape the folder)
    #   : * ? " < > |  reserved on Windows
    #   \x00-\x1f    control characters (newline, tab, NUL, ...)
    # Then trim leading/trailing spaces and dots (Windows drops trailing dots,
    # and a leading dot would make the note a hidden file).
    name = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", " ", title).strip(" .")
    # Collapse runs of whitespace into one space and cap length at 80 chars
    # so the full path stays well under OS limits.
    name = re.sub(r"\s+", " ", name)[:80] or "Untitled"
    return f"{date.today().isoformat()} {name}"


def create_note(folder: str, title: str, body: str) -> tuple[Path, bool]:
    """Write a new .md note. Returns (path, tracked). Never overwrites."""
    real = Path(folder).resolve(strict=True)
    if any(part in permissions.DENY_PARTS for part in real.parts):  # §6 denylist
        audit.record("blocked", path=folder, outcome="Blocked location")
        raise PermissionError("Blocked location")
    if not real.is_dir():
        raise NotADirectoryError("Choose a folder")
    base = _safe_name(title)
    text = (f"# {title.strip()}\n\n" if title.strip() else "") + body.rstrip() + "\n"
    for n in range(1, 100):
        target = real / (f"{base}.md" if n == 1 else f"{base} ({n}).md")
        try:
            with open(target, "x", encoding="utf-8") as f:  # exclusive: never overwrite
                f.write(text)
            break
        except FileExistsError:
            continue
    else:
        raise FileExistsError("Too many notes with this name")
    tracked = is_tracked(real)
    audit.record("note_created", path=str(target), outcome="tracked" if tracked else "not tracked")
    return target, tracked
