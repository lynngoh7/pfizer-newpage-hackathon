"""Audit log: every file read, block, search and session event, in memory only.

Safety rules (brief §6, "Audit log" and "No copies"):
  * Entries hold time, action, file path, the user's query and a short outcome.
    Never note content. `action` must be one of ACTIONS and `outcome` is capped,
    so there is no free-text field that could quietly carry note text.
  * Lives in this process only. Never written to disk. Gone on quit and on
    "forget everything" (session.forget calls clear()).

Called by: ingest (read / skipped / blocked), permissions (folder_added /
folder_removed / blocked), search and qa (search / ask), session (forget).
Read by: GET /api/audit (Trust panel).
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import asdict, dataclass

ACTIONS = frozenset({
    "read",            # a file was opened and parsed
    "skipped",         # file seen but not read (unsupported, empty, corrupt, encrypted)
    "blocked",         # path refused by the allowlist/denylist check
    "folder_added",
    "folder_removed",
    "search",
    "ask",
    "forget",          # the user cleared the session
    "open_in_editor",  # handed a file to the user's default app (the app never edits it)
    "note_created",    # the user saved a new note (the app's only write; never overwrites)
    "conflict_check",  # compared notes for disagreements (counts only)
})
MAX_ENTRIES = 5000     # bounded so a huge folder cannot grow memory without limit
MAX_OUTCOME = 80       # a reason like "corrupt PDF", never a passage


@dataclass(frozen=True)
class Entry:
    seq: int
    time: float
    action: str
    path: str | None
    query: str | None
    outcome: str


# FastAPI runs plain `def` routes in a thread pool, so guard shared state.
_lock = threading.Lock()
_entries: deque[Entry] = deque(maxlen=MAX_ENTRIES)
_seq = 0  # increases forever; the UI asks for "entries after seq N"


def record(action: str, path: str | None = None, query: str | None = None, outcome: str = "ok") -> None:
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action: {action!r}")
    global _seq
    with _lock:
        _seq += 1
        _entries.append(Entry(_seq, time.time(), action, path, query, outcome[:MAX_OUTCOME]))


def entries(after: int = 0) -> list[dict]:
    """Entries with seq > after, oldest first. Lets the UI poll for new lines only."""
    with _lock:
        return [asdict(e) for e in _entries if e.seq > after]


def clear() -> int:
    """Drop every entry. Returns how many were dropped. seq keeps counting so a
    polling UI never mistakes new entries for ones it has already shown."""
    with _lock:
        n = len(_entries)
        _entries.clear()
        return n
