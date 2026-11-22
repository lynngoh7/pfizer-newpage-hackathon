"""Find dated lines in notes for the Upcoming list on Home.

Reads passages through extractions.read_chunks (path-checked, re-read from the
original file) and returns each line that names a date, with the date resolved
to ISO. Nothing is stored; the list is rebuilt per request (One Rule: no copies).

Only explicit dates are read ("24 Nov", "Nov 24 2026", "2026-11-24") plus
weekdays ("Friday", "next Fri"), which are resolved against the note's own
date. Vague phrases ("end of month", "soon") are skipped rather than guessed.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import TypedDict

from .extractions import read_chunks

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
_DAY_MON = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MON}(?:,?\s+(\d{{4}}))?\b", re.I)
_MON_DAY = re.compile(rf"\b{_MON}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", re.I)
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_WEEKDAY = re.compile(r"\b(next\s+)?(mon|tue|wed|thu|fri|sat|sun)(?:day|s|sday|nesday|rsday|urday)?\b", re.I)
_TODO = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[([ xX])\]\s+")


class Dated(TypedDict):
    when: str      # ISO date the line refers to
    text: str      # the line, trimmed
    todo: bool     # an open checkbox, so a past date means overdue
    chunkID: int
    path: str
    noteDate: str


def _make(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _with_year(month: int, day: int, year: str | None, note: date) -> date | None:
    if year:
        return _make(int(year), month, day)
    found = _make(note.year, month, day)
    # "3 Jan" in a December note means next January.
    if found and found < note - timedelta(days=183):
        found = _make(note.year + 1, month, day)
    return found


def find_date(line: str, note: date) -> date | None:
    """Return the first date a line names, or None. Explicit dates win over weekdays."""
    if m := _ISO.search(line):
        return _make(int(m[1]), int(m[2]), int(m[3]))
    if m := _DAY_MON.search(line):
        return _with_year(_MONTHS[m[2][:3].lower()], int(m[1]), m[3], note)
    if m := _MON_DAY.search(line):
        return _with_year(_MONTHS[m[1][:3].lower()], int(m[2]), m[3], note)
    if m := _WEEKDAY.search(line):
        ahead = (_WEEKDAYS.index(m[2][:3].lower()) - note.weekday()) % 7 or 7
        return note + timedelta(days=ahead + (7 if m[1] and ahead < 7 else 0))
    return None


def upcoming() -> dict[str, list[Dated]]:
    found: list[Dated] = []
    for chunk in read_chunks():
        try:
            note = date.fromisoformat(chunk["date"][:10])
        except ValueError:
            continue
        for line in chunk["text"].splitlines():
            text = line.strip()
            # Headings and the note's own date line describe the note, not an event.
            if not text or text.startswith("#"):
                continue
            when = find_date(text, note)
            if when is None or when == note:
                continue
            todo = _TODO.match(line)
            if todo and todo[1].lower() == "x":
                continue  # done: nothing to come
            found.append({"when": when.isoformat(), "text": text, "todo": bool(todo),
                          "chunkID": chunk["chunkID"], "path": chunk["path"], "noteDate": chunk["date"]})
    found.sort(key=lambda d: d["when"])
    return {"items": found}
