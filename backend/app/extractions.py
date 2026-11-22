"""Read indexed passages for decision and to-do extraction.

Readable note text is re-read from its original file only when requested. It
is never copied into another session store.
"""
from __future__ import annotations

import re
from typing import TypedDict

from . import db


class Todo(TypedDict):
    task: str
    completed: bool
    chunkID: int
    path: str
    date: str
    start: int
    end: int


class Decision(TypedDict):
    text: str
    chunkID: int
    path: str
    date: str
    start: int
    end: int


class IndexedChunk(TypedDict): #recieved from database
    chunkID: int
    path: str
    date: str
    start: int
    end: int
    text: str


def read_chunk(chunk_id: int) -> IndexedChunk | None:
    """Return one live indexed passage with its source metadata.

    Unknown chunks, changed files, and inaccessible files are omitted rather
    than returning potentially stale or unauthorized text.
    """
    info = db.chunk_info(chunk_id) #get row of database via id
    if info is None:
        return None
    try:
        text = db.passage(chunk_id)
    except OSError:
        return None
    if text is None:
        return None
    return { #return database info as a IndexedChunk
        "chunkID": info["chunkID"],
        "path": info["filePath"],
        "date": info["noteDate"],
        "start": info["start"],
        "end": info["end"],
        "text": text,
    }


def read_chunks() -> list[IndexedChunk]:
    """Return all currently readable indexed passages in index order."""
    chunks = []
    for chunk_id in db.chunk_ids():
        chunk = read_chunk(chunk_id)
        if chunk is not None:
            chunks.append(chunk)
    return chunks

#regex magic
_TODO = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[([ xX])\]\s+(.+?)\s*$")


def todos() -> dict[str, list[Todo]]:
    """Extract Markdown checkbox items from currently readable passages."""
    extracted: list[Todo] = []
    for chunk in read_chunks():
        in_fence = False
        fence_marker = ""
        for line in chunk["text"].splitlines():
            stripped = line.lstrip()
            if stripped.startswith(("```", "~~~")): 
                marker = stripped[:3]
                if not in_fence:
                    in_fence = True
                    fence_marker = marker
                elif marker == fence_marker:
                    in_fence = False
                continue
            if in_fence:
                continue
            match = _TODO.match(line) #if chunk contains suspected todo
            if match is None:
                continue
            task = match.group(2).strip() #get
            if not task:
                continue
            extracted.append({
                "task": task,
                "completed": match.group(1).lower() == "x", #check if completed
                "chunkID": chunk["chunkID"],
                "path": chunk["path"],
                "date": chunk["date"],
                "start": chunk["start"],
                "end": chunk["end"],
            })
    return {"todos": extracted}

# A Markdown heading, a "DECISION:" label, and a list item (which ends a decision paragraph)
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_DECISION_LABEL = re.compile(r"^\s*(?:[-*+]\s*)?(?:\*\*)?DECISION(?:S)?\s*:\s*(.*?)(?:\*\*)?\s*$", re.IGNORECASE)
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _decision_text(lines: list[str]) -> str:
    """Return a heading's first prose paragraph, excluding following lists."""
    paragraph = []
    for line in lines:
        if not line.strip() or _LIST_ITEM.match(line):
            break
        paragraph.append(line.strip())
    return " ".join(paragraph).strip()


def decisions() -> dict[str, list[Decision]]:
    """Extract explicit decision sections and DECISION: labels from passages."""
    extracted: list[Decision] = []
    for chunk in read_chunks():
        lines = chunk["text"].splitlines()
        in_fence = False
        fence_marker = ""
        index = 0
        while index < len(lines):
            line = lines[index]
            stripped = line.lstrip()
            # A matching-looking heading inside an example/code block is not a decision.
            if stripped.startswith(("```", "~~~")):
                marker = stripped[:3]
                if not in_fence:
                    in_fence = True
                    fence_marker = marker
                elif marker == fence_marker:
                    in_fence = False
                index += 1
                continue
            if in_fence:
                index += 1
                continue

            decision_text = None
            heading = _HEADING.match(line)
            if heading and heading.group(2).strip().casefold() in {"decision", "decisions"}:
                # Only take the first prose paragraph under the heading; stop
                # before the next section, blank line, or action list.
                paragraph_lines = []
                index += 1
                while index < len(lines):
                    candidate = lines[index]
                    if _HEADING.match(candidate) or not candidate.strip() or _LIST_ITEM.match(candidate):
                        break
                    paragraph_lines.append(candidate)
                    index += 1
                decision_text = _decision_text(paragraph_lines)
                if decision_text:
                    extracted.append({
                        "text": decision_text,
                        "chunkID": chunk["chunkID"],
                        "path": chunk["path"],
                        "date": chunk["date"],
                        "start": chunk["start"],
                        "end": chunk["end"],
                    })
                continue
            else:
                # Also support inline labels such as "- DECISION: ..." and
                # bold labels used in plain-text meeting notes.
                label = _DECISION_LABEL.match(line)
                if label:
                    decision_text = label.group(1).strip()
                    if not decision_text:
                        following = []
                        index += 1
                        while index < len(lines) and lines[index].strip() and not _LIST_ITEM.match(lines[index]):
                            following.append(lines[index])
                            index += 1
                        decision_text = _decision_text(following)

            if decision_text:
                extracted.append({
                    "text": decision_text,
                    "chunkID": chunk["chunkID"],
                    "path": chunk["path"],
                    "date": chunk["date"],
                    "start": chunk["start"],
                    "end": chunk["end"],
                })
            index += 1
    return {"decisions": extracted}
