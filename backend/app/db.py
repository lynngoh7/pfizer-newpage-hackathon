"""The session index: in-memory SQLite with Files, Chunks, Groups and keyword search.

Schema and reasons in docs/DB_DESIGN.md. Rules (brief §6):
  * No copies: the database is `:memory:`, never a file. No table holds readable
    note text. Chunks are positions (file + lines/page); passage() re-reads them.
  * Keyword search is a *contentless* FTS5 table: word lists only, no text.
  * Meaning search: vectors are kept in a Python dict (memory only). sqlite-vec
    needs `enable_load_extension`, which our current Python lacks (brief §9);
    swap it in here once packaging allows. At ~1000 chunks a plain dot product
    takes well under a second.
  * Data wipe / revoke: clear() is registered with session.on_forget and
    drop_under() with permissions.on_revoke, so both empty the index at once.
  * Every file read goes through permissions.resolve_and_check.

Called by: the ingest pipeline (build), search/qa (keyword, semantic, passage).
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path

from . import permissions, session

SCHEMA = """
PRAGMA foreign_keys = ON;   -- SQLite ignores FKs without this; revoke relies on the cascade
CREATE TABLE Files (
    fileID   INTEGER PRIMARY KEY,
    filePath TEXT NOT NULL UNIQUE,
    mtime    REAL NOT NULL,
    hash     TEXT NOT NULL,
    noteDate TEXT NOT NULL      -- ISO date: from the file name, else mtime
);
CREATE TABLE Groups (
    groupID INTEGER PRIMARY KEY,
    topic   TEXT NOT NULL,
    named   INTEGER NOT NULL DEFAULT 0   -- 0 = placeholder "Group N", named on first topics() call
);
CREATE TABLE Chunks (
    chunkID INTEGER PRIMARY KEY,
    fileID  INTEGER NOT NULL REFERENCES Files(fileID) ON DELETE CASCADE,
    start   INTEGER NOT NULL,
    "end"   INTEGER NOT NULL,
    groupID INTEGER REFERENCES Groups(groupID) ON DELETE SET NULL
);
CREATE INDEX chunks_file ON Chunks(fileID);
CREATE INDEX chunks_group ON Chunks(groupID);
-- No copies: content='' keeps the word index but not the text.
CREATE VIRTUAL TABLE chunks_fts USING fts5(text, content='');
"""

_DATE = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")
_lock = threading.Lock()
_db: sqlite3.Connection
_vecs: dict[int, list[float]] = {}


def _connect() -> None:
    global _db
    _db = sqlite3.connect(":memory:", check_same_thread=False)
    _db.executescript(SCHEMA)


_connect()


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def note_date(path: Path, mtime: float) -> str:
    """The date the note is about. Copying files resets mtime, so a date in
    the file name ("2026-09-22 Lighthouse vendor decision.md") wins."""
    m = _DATE.search(path.name)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            pass
    return datetime.fromtimestamp(mtime).date().isoformat()


# ---- writing -------------------------------------------------------------

def add_file(file_path: str, chunks) -> list[int]:
    """Index one file's chunks (ingest.Chunk objects, all from this file).
    Replaces any earlier version of the file. Sets chunk.chunkID and returns
    the IDs. The chunk text goes into FTS as words only and is not kept."""
    real = permissions.resolve_and_check(file_path)
    st = real.stat()
    with _lock, _db:
        old = _db.execute("SELECT fileID FROM Files WHERE filePath = ?", (str(real),)).fetchone()
        if old:
            _drop_files([old[0]])
        fid = _db.execute(
            "INSERT INTO Files (filePath, mtime, hash, noteDate) VALUES (?, ?, ?, ?)",
            (str(real), st.st_mtime, _hash(real), note_date(real, st.st_mtime)),
        ).lastrowid
        ids = []
        for c in chunks:
            cid = _db.execute('INSERT INTO Chunks (fileID, start, "end") VALUES (?, ?, ?)',
                              (fid, c.start, c.end)).lastrowid
            _db.execute("INSERT INTO chunks_fts (rowid, text) VALUES (?, ?)", (cid, c.text))
            c.chunkID = cid
            ids.append(cid)
    return ids


def set_groups(rows: list[dict], chunks) -> None:
    """Store group.group() output. Replaces all groups (grouping runs over
    the whole index). Chunks need chunkID and groupID set."""
    with _lock, _db:
        _db.execute("UPDATE Chunks SET groupID = NULL")
        _db.execute("DELETE FROM Groups")
        _db.executemany("INSERT INTO Groups (groupID, topic) VALUES (?, ?)",
                        [(r["groupID"], r["topic"]) for r in rows])
        _db.executemany("UPDATE Chunks SET groupID = ? WHERE chunkID = ?",
                        [(c.groupID, c.chunkID) for c in chunks if getattr(c, "groupID", None)])


def add_vectors(chunk_ids: list[int], vecs: list[list[float]]) -> None:
    """Unit-length vectors from group.embed, one per chunk."""
    with _lock:
        _vecs.update(zip(chunk_ids, vecs))


def topics() -> list[dict]:
    """Groups with their topics, naming any still unnamed (one LLM call
    each). Called by the Topics/Summary view, not during indexing, so the
    index build never waits on the LLM. Text for naming is re-read from the
    files (No copies), up to 4 chunks per group."""
    from types import SimpleNamespace

    from . import group

    with _lock:
        todo = [r[0] for r in _db.execute("SELECT groupID FROM Groups WHERE named = 0")]
    for gid in todo:
        with _lock:
            cids = [r[0] for r in _db.execute(
                "SELECT chunkID FROM Chunks WHERE groupID = ? ORDER BY chunkID LIMIT 4", (gid,))]
        texts = []
        for cid in cids:
            try:
                t = passage(cid)
            except (OSError, PermissionError):
                t = None
            if t:
                texts.append(SimpleNamespace(text=t))
        if not texts:
            continue
        try:
            topic = group.name(texts)
        except OSError:  # Ollama down: keep the placeholder, try again next time
            break
        with _lock, _db:  # the group may have been dropped meanwhile; UPDATE is then a no-op
            _db.execute("UPDATE Groups SET topic = ?, named = 1 WHERE groupID = ?", (topic, gid))
    with _lock:
        return [dict(zip(("groupID", "topic", "named", "chunks"), r)) for r in _db.execute(
            "SELECT g.groupID, g.topic, g.named, count(c.chunkID) FROM Groups g "
            "LEFT JOIN Chunks c USING (groupID) GROUP BY g.groupID ORDER BY g.groupID")]


def build(chunks) -> dict:
    """Index a whole ingest run: files, keyword search, vectors, groups.
    Needs Ollama for the vectors. Groups get placeholder names until topics()."""
    from . import group  # imported here so keyword search works without Ollama code loaded

    by_file: dict[str, list] = {}
    for c in chunks:
        by_file.setdefault(c.filePath, []).append(c)
    indexed = []
    for path, cs in by_file.items():
        try:
            add_file(path, cs)
            indexed += cs
        except (OSError, PermissionError):
            continue  # moved or no longer allowed since it was read
    vecs = group.embed(indexed) if indexed else []
    add_vectors([c.chunkID for c in indexed], vecs)
    set_groups(group.group(indexed, vecs=vecs), indexed)
    return stats()


# ---- removing ------------------------------------------------------------

def _drop_files(fids: list[int]) -> int:
    """Caller holds _lock inside a transaction."""
    if not fids:
        return 0
    marks = ",".join("?" * len(fids))
    cids = [r[0] for r in _db.execute(f"SELECT chunkID FROM Chunks WHERE fileID IN ({marks})", fids)]
    _db.execute(f"DELETE FROM Files WHERE fileID IN ({marks})", fids)  # cascades to Chunks
    _db.execute("DELETE FROM Groups WHERE groupID NOT IN "
                "(SELECT groupID FROM Chunks WHERE groupID IS NOT NULL)")
    for cid in cids:
        _vecs.pop(cid, None)
    _rebuild_fts()
    return len(cids)


def _rebuild_fts() -> None:
    """Our SQLite (3.35) cannot delete single rows from a contentless FTS
    table, so after a removal we rebuild it from the remaining chunks,
    re-read from their files. Removals are rare (revoke, changed file)."""
    _db.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('delete-all')")
    rows = _db.execute('SELECT c.chunkID, f.filePath, f.hash, c.start, c."end" '
                       "FROM Chunks c JOIN Files f USING (fileID) ORDER BY f.fileID").fetchall()
    cache: dict[str, list[str] | None] = {}
    for cid, path, h, start, end in rows:
        if path not in cache:
            cache[path] = _units(path, h)
        units = cache[path]
        if units is not None:  # a changed file stays out of search until re-indexed
            _db.execute("INSERT INTO chunks_fts (rowid, text) VALUES (?, ?)",
                        (cid, "".join(units[start:end + 1])))


def drop_under(path: Path) -> int:
    """Revoke hook: drop every file equal to or inside `path`."""
    with _lock, _db:
        fids = [fid for fid, p in _db.execute("SELECT fileID, filePath FROM Files")
                if Path(p) == path or Path(p).is_relative_to(path)]
        return _drop_files(fids)


def clear() -> int:
    """Forget-everything hook: a fresh empty database."""
    global _db
    with _lock:
        n = _db.execute("SELECT count(*) FROM Chunks").fetchone()[0]
        _db.close()
        _vecs.clear()
        _connect()
    return n


permissions.on_revoke("index", drop_under)
session.on_forget("index", clear)


# ---- reading -------------------------------------------------------------

def _units(path: str, expected_hash: str) -> list[str] | None:
    """The file as a list of lines (pages for PDF), or None if it changed
    since indexing, so stale line numbers never show the wrong passage."""
    real = permissions.resolve_and_check(path)
    if _hash(real) != expected_hash:
        return None
    suffix = real.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        return [p.extract_text() or "" for p in PdfReader(str(real)).pages]
    if suffix == ".docx":
        from markitdown import MarkItDown
        return MarkItDown(enable_plugins=False).convert_local(str(real)).text_content.splitlines(keepends=True)
    return real.read_text().splitlines(keepends=True)


def passage(chunk_id: int) -> str | None:
    """Re-read a chunk's text from its file. None if the chunk is unknown or
    the file changed since indexing (re-index it). Raises PermissionError if
    the file is no longer allowed."""
    with _lock:
        row = _db.execute('SELECT f.filePath, f.hash, c.start, c."end" FROM Chunks c '
                          "JOIN Files f USING (fileID) WHERE c.chunkID = ?", (chunk_id,)).fetchone()
    if row is None:
        return None
    path, h, start, end = row
    try:
        units = _units(path, h)
    except FileNotFoundError:
        return None
    return None if units is None else "".join(units[start:end + 1])


def chunk_info(chunk_id: int) -> dict | None:
    with _lock:
        row = _db.execute(
            'SELECT c.chunkID, f.filePath, f.noteDate, c.start, c."end", c.groupID, g.topic '
            "FROM Chunks c JOIN Files f USING (fileID) LEFT JOIN Groups g USING (groupID) "
            "WHERE c.chunkID = ?", (chunk_id,)).fetchone()
    if row is None:
        return None
    return dict(zip(("chunkID", "filePath", "noteDate", "start", "end", "groupID", "topic"), row))


def keyword(query: str, k: int = 10) -> list[int]:
    """Chunk IDs for the best keyword matches (bm25). Each word is quoted, so
    user input can never be read as FTS5 syntax."""
    words = re.findall(r"\w+", query)
    if not words:
        return []
    match = " OR ".join('"' + w + '"' for w in words)
    with _lock:
        return [r[0] for r in _db.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?", (match, k))]


def semantic(query_vec: list[float], k: int = 10) -> list[int]:
    """Chunk IDs closest in meaning to a unit-length query vector."""
    with _lock:
        scored = [(sum(a * b for a, b in zip(query_vec, v)), cid) for cid, v in _vecs.items()]
    scored.sort(reverse=True)
    return [cid for _, cid in scored[:k]]


def stats() -> dict:
    with _lock:
        f, c, g = (_db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("Files", "Chunks", "Groups"))
    return {"files": f, "chunks": c, "groups": g, "vectors": len(_vecs)}
