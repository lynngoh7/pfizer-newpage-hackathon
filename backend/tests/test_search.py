"""search: folder walk, keyword search, Ollama fallback, revoke/forget, API."""
import pytest
from fastapi.testclient import TestClient

from app import audit, db, group, ingest, permissions, search, session
from app.config import Settings
from app.main import create_app

TOKEN = "t" * 48
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _no_ollama(*a, **k):
    raise ConnectionRefusedError("ollama off")


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    permissions.on_revoke("index", db.drop_under)   # test_privacy_edges clears hooks
    session.on_forget("index", db.clear)
    monkeypatch.setattr(group, "_post", _no_ollama)
    monkeypatch.setattr(ingest, "MERGE_CHARS", 0)  # keep the tiny test passages apart
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "2026-09-22 vendor decision.md").write_text(
        "# Decision\nWe chose Acme as the Lighthouse vendor.\n\n# Budget\nReduced funding for Q4.\n")
    (notes / "standup.txt").write_text("Shipped the login page.\n\nAcme contract review pending.\n")
    (notes / ".hidden.md").write_text("# secret\nAcme hidden\n")
    (notes / "image.png").write_bytes(b"\x89PNG")
    permissions.allowed_folders.add(notes.resolve())
    db.clear(); audit.clear()
    yield notes
    search._bump()  # stop any background build from this test
    db.clear(); ingest.chunks.clear(); permissions.allowed_folders.clear()


def test_reindex_reads_supported_visible_files_and_keeps_no_text(_clean):
    stats = search.reindex(background=False)
    assert stats["read"] == 2 and stats["files"] == 2 and stats["phase"] == "keyword_only"
    assert ingest.chunks == []  # note text dropped once indexed


def test_keyword_search_returns_source_cards_reread_from_file(_clean):
    search.reindex(background=False)
    r = search.search("Lighthouse vendor")
    assert r["status"] == "ok" and r["answer"] is None
    top = r["sources"][0]
    assert top["path"].endswith("vendor decision.md")
    assert top["where"] == "# Decision"
    assert top["date"] == "2026-09-22"
    assert "Acme" in top["snippet"]
    assert audit.entries()[-1]["action"] == "search"


def test_no_match_says_so(_clean):
    search.reindex(background=False)
    assert search.search("zebra")["status"] == "no_support"
    assert search.search("!!!")["sources"] == []   # no words, not an FTS error


def test_fts_syntax_in_query_is_treated_as_words(_clean):
    search.reindex(background=False)
    assert search.search('Acme" OR NEAR(x') ["status"] == "ok"


def test_edited_file_is_not_shown_with_stale_lines(_clean):
    search.reindex(background=False)
    (_clean / "standup.txt").write_text("totally different\n")
    assert all("standup" not in s["path"] for s in search.search("Acme")["sources"])


def test_revoke_drops_results_at_once(_clean):
    search.reindex(background=False)
    permissions.revoke_path(str(_clean))
    assert search.search("Acme")["status"] == "no_support"
    assert db.stats()["chunks"] == 0


def test_forget_empties_index(_clean):
    search.reindex(background=False)
    session.forget()
    assert db.stats()["files"] == 0


def test_rrf_merges_keyword_and_meaning(_clean, monkeypatch):
    search.reindex(background=False)
    ids = db.keyword("Acme", 10)
    monkeypatch.setattr(search, "_query_vec", lambda q: [1.0])
    monkeypatch.setattr(db, "semantic", lambda v, k: list(reversed(ids)))
    assert set(search.rank("Acme")) == set(ids)


def test_api_index_and_search(_clean):
    c = TestClient(create_app(Settings(port=0, session_token=TOKEN)))
    assert c.get("/api/search?q=Acme").status_code == 401
    assert c.post("/api/index", headers=AUTH).json()["files"] == 2
    assert c.get("/api/index", headers=AUTH).json()["chunks"] >= 3
    body = c.get("/api/search", params={"q": "reduced funding"}, headers=AUTH).json()
    assert body["sources"][0]["where"] == "# Budget"
    assert c.get("/api/search?q=", headers=AUTH).status_code == 422


def _fake_ollama(path, body):
    if path == "/api/embed":
        return {"embeddings": [[1.0, 0.0] for _ in body["input"]]}
    return {"message": {"content": "Vendors"}}


def test_meaning_build_runs_after_keyword_is_ready(_clean, monkeypatch):
    monkeypatch.setattr(group, "_post", _fake_ollama)
    stats = search.reindex(background=False)
    assert search.status()["phase"] == "ready"
    assert db.stats()["vectors"] == stats["chunks"] and db.stats()["groups"] >= 1


def test_forget_mid_build_discards_the_build(_clean, monkeypatch):
    calls = []

    def embed_then_forget(path, body):
        if not calls:
            session.forget()   # user hits "Forget everything" during embedding
        calls.append(path)
        return _fake_ollama(path, body)

    monkeypatch.setattr(group, "_post", embed_then_forget)
    search.reindex(background=False)
    assert db.stats() == {"files": 0, "chunks": 0, "groups": 0, "vectors": 0}
    assert search.status()["phase"] == "empty"


def test_index_returns_before_meaning_search_is_built(_clean, monkeypatch):
    import threading
    gate = threading.Event()
    monkeypatch.setattr(group, "_post", lambda p, b: (gate.wait(5), _fake_ollama(p, b))[1])
    stats = search.reindex()
    assert stats["phase"] == "meaning" and stats["chunks"] >= 3
    assert search.search("Acme")["status"] == "ok"   # keyword works meanwhile
    gate.set()
