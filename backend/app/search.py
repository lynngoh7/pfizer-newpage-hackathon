"""Search: build the session index and answer keyword/meaning searches.

reindex() reads the allowed folders (ingest) into db. search() merges
keyword (FTS5 bm25) and meaning (vector) results by reciprocal rank fusion,
then re-reads each passage from its file (No copies, §6).
Keyword search is ready in seconds; meaning search follows in the background. Response shape:
docs/API_SHAPES.md.

Meaning search needs Ollama. If it is not running, search falls back to
keyword only instead of failing.

Called by: api.py (/api/index, /api/search); qa.py for retrieval.
"""
from __future__ import annotations

import math
import threading

from . import audit, db, group, ingest, session

K = 5            # sources returned (API_SHAPES: 5 at most)
POOL = 20        # candidates taken from each ranker before merging
RRF_K = 60       # standard reciprocal-rank-fusion constant
MAX_SNIPPET = 300

_build_lock = threading.Lock()
_gen = 0          # bumped by every reindex/forget; a stale background build stops
_progress = {"phase": "empty", "done": 0, "total": 0}


def _bump(*_) -> None:
    global _gen
    _gen += 1
    _progress.update(phase="empty", done=0, total=0)


session.on_forget("search", _bump)  # forget mid-build must not let vectors come back


def reindex(background: bool = True) -> dict:
    """Rebuild the index from the allowed folders. Keyword search is ready
    when this returns (seconds). Vectors and topic groups need Ollama and
    take longer, so they are built in a background thread; progress is in
    status(). background=False waits for them (tests, scripts)."""
    with _build_lock:
        _bump()
        gen = _gen
        db.clear()
        files = ingest.ingestAllowed()
        by_file: dict[str, list] = {}
        for c in ingest.chunks:
            by_file.setdefault(c.filePath, []).append(c)
        indexed = []
        for path, cs in by_file.items():
            try:
                db.add_file(path, cs)
                indexed += cs
            except (OSError, PermissionError):
                continue  # moved or no longer allowed since it was read
        # The shared chunk list holds note text; only the build below needs it.
        ingest.chunks.clear()
        _progress.update(phase="meaning", done=0, total=len(indexed))
    if background:
        threading.Thread(target=_build_meaning, args=(indexed, gen), daemon=True).start()
    else:
        _build_meaning(indexed, gen)
    return {**db.stats(), "read": files, **status()}


def _build_meaning(chunks, gen: int) -> None:
    """Embed and group in batches. Drops its work (and the note text it holds)
    if a reindex, revoke or forget happened meanwhile."""
    try:
        vecs: list[list[float]] = []
        for i in range(0, len(chunks), group.BATCH):
            if gen != _gen:
                return
            vecs += group.embed(chunks[i:i + group.BATCH])
            _progress["done"] = len(vecs)
        with _build_lock:
            if gen != _gen:
                return
            # A folder revoked mid-build: keep only chunks still in the index.
            live = [(c, v) for c, v in zip(chunks, vecs) if db.chunk_info(c.chunkID)]
            db.add_vectors([c.chunkID for c, _ in live], [v for _, v in live])
        kept = [c for c, _ in live]
        _progress["phase"] = "grouping"
        rows = group.group(kept, vecs=[v for _, v in live])
        with _build_lock:
            if gen == _gen:
                db.set_groups(rows, kept)
                _progress["phase"] = "ready"
    except OSError:  # Ollama not running: keyword search still works
        if gen == _gen:
            _progress["phase"] = "keyword_only"


def status() -> dict:
    """Index build progress for the UI: phase is empty, meaning (embedding
    done/total), grouping, ready, or keyword_only (Ollama not running)."""
    return dict(_progress)


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
