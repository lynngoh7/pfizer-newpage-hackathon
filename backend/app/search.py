"""Search: build the session index and answer keyword/meaning searches.

reindex() reads the allowed folders (ingest) into db. search() merges
keyword (FTS5 bm25) and meaning (vector) results by reciprocal rank fusion,
then re-reads each passage from its file (No copies, §6). Response shape:
docs/API_SHAPES.md.

Meaning search needs Ollama. If it is not running, both functions fall
back to keyword only instead of failing.

Called by: api.py (/api/index, /api/search); qa.py for retrieval.
"""
from __future__ import annotations

import math
import threading

from . import audit, db, group, ingest

K = 5            # sources returned (API_SHAPES: 5 at most)
POOL = 20        # candidates taken from each ranker before merging
RRF_K = 60       # standard reciprocal-rank-fusion constant
MAX_SNIPPET = 300

_build_lock = threading.Lock()


def reindex() -> dict:
    """Rebuild the index from scratch from the allowed folders."""
    with _build_lock:
        db.clear()
        files = ingest.ingestAllowed()
        try:
            stats = db.build(ingest.chunks)
            semantic = True
        except OSError:  # Ollama not running: db.build already added the files
            stats, semantic = db.stats(), False
        # The chunk list holds note text; the index no longer needs it.
        ingest.chunks.clear()
    return {**stats, "read": files, "semantic": semantic}


def _query_vec(query: str) -> list[float] | None:
    if not db.stats()["vectors"]:
        return None
    try:
        v = group._post("/api/embed", {"model": group.EMBED_MODEL,
                                       "input": ["search_query: " + query]})["embeddings"][0]
    except OSError:
        return None
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def rank(query: str, k: int = K) -> list[int]:
    """Chunk IDs, best first: keyword and meaning merged by RRF."""
    lists = [db.keyword(query, POOL)]
    vec = _query_vec(query)
    if vec is not None:
        lists.append(db.semantic(vec, POOL))
    score: dict[int, float] = {}
    for ids in lists:
        for r, cid in enumerate(ids):
            score[cid] = score.get(cid, 0.0) + 1.0 / (RRF_K + r)
    return sorted(score, key=score.get, reverse=True)[:k]


def _where(info: dict, text: str) -> str:
    if info["filePath"].lower().endswith(".pdf"):
        return f"page {info['start'] + 1}"
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    if first.startswith("#"):
        return first.strip()
    return f"lines {info['start'] + 1}–{info['end'] + 1}"


def source(cid: int) -> dict | None:
    """One source card, snippet re-read from the file now. None if the file
    changed, moved or is no longer allowed."""
    info = db.chunk_info(cid)
    if info is None:
        return None
    try:
        text = db.passage(cid)
    except (OSError, PermissionError):
        return None
    if text is None:
        return None
    return {"chunkID": cid, "path": info["filePath"], "date": info["noteDate"],
            "where": _where(info, text), "snippet": text.strip()[:MAX_SNIPPET], "flag": None}


def search(query: str, k: int = K) -> dict:
    sources = [s for s in map(source, rank(query, k)) if s]
    audit.record("search", query=query, outcome=f"{len(sources)} results")
    return {"status": "ok" if sources else "no_support", "answer": None, "sources": sources}
