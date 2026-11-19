""""Forget everything": one place that clears all session state.

Safety rule (brief §6, "Data wipe" and "No copies"): every module that holds
anything from the user's notes (index, folder grants, model context) registers
a reset function here. forget() runs them all, so a new module cannot be left
out by accident as long as it registers.

To register (in your module, at import time):
    from . import session
    session.on_forget("index", drop_everything)   # returns a count or None

Called by: DELETE /api/session (Trust panel and Settings).
"""
from __future__ import annotations

from typing import Callable

from . import audit

_resets: dict[str, Callable[[], int | None]] = {}


def on_forget(name: str, reset: Callable[[], int | None]) -> None:
    _resets[name] = reset


def forget() -> dict[str, int | None]:
    """Run every reset, clear the audit log, and report what was cleared.
    The audit log is cleared last, then gets one line saying it happened, so
    the user sees the confirmation in the log itself."""
    cleared = {name: reset() for name, reset in _resets.items()}
    cleared["activity_log"] = audit.clear()
    audit.record("forget")
    return cleared
