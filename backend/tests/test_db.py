"""db: in-memory index. Keyword search, no stored text, revoke/forget, changed files."""
import pytest

from app import audit, db, ingest, permissions, session


@pytest.fixture(autouse=True)
def clean(tmp_path):
    db.clear()
    ingest.chunks.clear()
    permissions.allowed_folders.clear()
    # other tests clear the hooks; put ours back
    permissions.on_revoke("index", db.drop_under)
    session.on_forget("index", db.clear)
    yield
    db.clear()
    ingest.chunks.clear()
    permissions.allowed_folders.clear()
    audit.clear()


def index(folder, files: dict[str, str]):
    folder.mkdir(exist_ok=True)
    permissions.grant_path(str(folder))
    for name, text in files.items():
        p = folder / name
        p.write_text(text)
        before = len(ingest.chunks)
        ingest.chunkFile(str(p))
        db.add_file(str(p), ingest.chunks[before:])


def test_keyword_search_finds_the_chunk_and_passage_rereads_it(tmp_path):
    index(tmp_path / "n", {"2026-09-22 vendor.md": "# Vendor\nWe chose Corvid.\n# Budget\nReduced funding.\n"})
    [cid] = db.keyword("corvid")
    assert db.passage(cid) == "# Vendor\nWe chose Corvid.\n"
    assert db.chunk_info(cid)["noteDate"] == "2026-09-22"


def test_no_note_text_is_stored_in_any_table(tmp_path):
    index(tmp_path / "n", {"a.md": "# A\nsecretword here\n"})
    dump = "\n".join(db._db.iterdump())
    assert "secretword" not in dump
    assert db.keyword("secretword")  # still searchable


def test_user_input_is_never_fts_syntax(tmp_path):
    index(tmp_path / "n", {"a.txt": "budget cut\n"})
    for q in ['budget" OR', "NEAR(", "*", "a AND", ""]:
        db.keyword(q)  # must not raise


def test_revoke_drops_chunks_groups_vectors_and_search(tmp_path):
    index(tmp_path / "keep", {"k.txt": "alpha note\n"})
    index(tmp_path / "gone", {"g.txt": "beta note\n"})
    [g] = db.keyword("beta")
    db.add_vectors([g], [[1.0]])
    permissions.revoke_path(str(tmp_path / "gone"))
    assert db.keyword("beta") == []
    assert db.keyword("alpha")
    assert db.stats() == {"files": 1, "chunks": 1, "groups": 0, "vectors": 0}


def test_forget_empties_the_index(tmp_path):
    index(tmp_path / "n", {"a.txt": "alpha\n"})
    session.forget()
    assert db.stats()["chunks"] == 0 and db.keyword("alpha") == []


def test_changed_file_never_shows_a_stale_passage(tmp_path):
    index(tmp_path / "n", {"a.txt": "old line\n"})
    [cid] = db.keyword("old")
    (tmp_path / "n" / "a.txt").write_text("new first line\nold line\n")
    assert db.passage(cid) is None


def test_reindexing_a_file_replaces_it(tmp_path):
    index(tmp_path / "n", {"a.txt": "first\n"})
    index(tmp_path / "n", {"a.txt": "second\n"})
    assert db.keyword("first") == [] and db.keyword("second")
    assert db.stats()["files"] == 1


def test_groups_and_semantic_search(tmp_path):
    index(tmp_path / "n", {"a.txt": "one\n\ntwo\n"})
    for c, gid in zip(ingest.chunks, (1, 2)):
        c.groupID = gid
    db.set_groups([{"groupID": 1, "topic": "A"}, {"groupID": 2, "topic": "B"}], ingest.chunks)
    db.add_vectors([c.chunkID for c in ingest.chunks], [[1.0, 0.0], [0.0, 1.0]])
    assert db.semantic([0.0, 1.0], k=1) == [ingest.chunks[1].chunkID]
    assert db.chunk_info(ingest.chunks[0].chunkID)["topic"] == "A"


def test_date_from_name_else_mtime(tmp_path):
    p = tmp_path / "Copy of 2026-10-20 rethink.md"
    assert db.note_date(p, 0) == "2026-10-20"
    assert db.note_date(tmp_path / "no date.txt", 1_790_000_000) == "2026-09-21"


def test_groups_are_named_lazily_from_reread_text(tmp_path, monkeypatch):
    from app import group
    index(tmp_path / "n", {"a.txt": "alpha\n\nbeta\n"})
    for c in ingest.chunks:
        c.groupID = 1
    db.set_groups([{"groupID": 1, "topic": group.placeholder(1)}], ingest.chunks)
    seen = []
    monkeypatch.setattr(group, "name", lambda cs: seen.append([c.text for c in cs]) or "Greek letters")
    assert db.topics() == [{"groupID": 1, "topic": "Greek letters", "named": 1, "chunks": 2}]
    db.topics()  # already named: no second LLM call
    assert seen == [["alpha\n", "beta\n"]]


def test_topics_keep_placeholder_when_ollama_is_down(tmp_path, monkeypatch):
    from app import group
    index(tmp_path / "n", {"a.txt": "alpha\n"})
    ingest.chunks[0].groupID = 1
    db.set_groups([{"groupID": 1, "topic": "Group 1"}], ingest.chunks)
    monkeypatch.setattr(group, "name", lambda cs: (_ for _ in ()).throw(OSError()))
    assert db.topics()[0]["topic"] == "Group 1"
