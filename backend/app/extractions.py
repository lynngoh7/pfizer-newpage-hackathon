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
