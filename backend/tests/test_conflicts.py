"""conflicts: pairing, verified quotes, injection-safe parsing, flags, forget."""
import json

import pytest

from app import audit, conflicts, db, group, ingest, permissions, search, session


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    permissions.on_revoke("index", db.drop_under)
    session.on_forget("index", db.clear)
    session.on_forget("conflicts", conflicts.reset)
    monkeypatch.setattr(ingest, "MERGE_CHARS", 0)
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "2026-09-22 vendor.md").write_text("# Decision\nWe chose Corvid as the vendor.\n")
    (notes / "2026-10-20 rethink.md").write_text("# Decision\nSwitched to Ledgerly as the vendor.\n")
    permissions.allowed_folders.add(notes.resolve())

    def fake_post(path, body):
        if path == "/api/embed":  # everything identical: one group, similarity 1
            return {"embeddings": [[1.0, 0.0] for _ in body["input"]]}
        return {"response": json.dumps(_reply)}
    monkeypatch.setattr(group, "_post", fake_post)
    monkeypatch.setattr(conflicts, "start", lambda: None)  # tests run _scan directly
    db.clear(); audit.clear(); conflicts.reset()
    yield notes
    search._bump(); db.clear(); conflicts.reset(); permissions.allowed_folders.clear()


_reply: dict = {}


def _scan(reply):
    _reply.clear(); _reply.update(reply)
    search.reindex(background=False)
    conflicts._scan(conflicts._gen)
    return conflicts.report()


def _ids():
    s = {r["path"].split("/")[-1]: r["chunkID"] for r in search.search("vendor")["sources"]}
    return s["2026-09-22 vendor.md"], s["2026-10-20 rethink.md"]


def test_superseded_pair_found_and_flags_search_results(_clean):
    r = _scan({"relation": "replaces", "older_quote": "We chose Corvid",
               "newer_quote": "Switched to Ledgerly", "summary": "Vendor changed"})
    assert r["phase"] == "done" and len(r["items"]) == 1
    item = r["items"][0]
    assert item["kind"] == "superseded"
    assert item["older"]["path"].endswith("vendor.md") and item["newer"]["date"] == "2026-10-20"
    old, new = _ids()
    assert conflicts.flag(old) == "superseded" and conflicts.flag(new) == "newer"
    assert audit.entries()[-1]["action"] == "search"
    assert any(e["action"] == "conflict_check" for e in audit.entries())


def test_unverified_quote_is_dropped(_clean):
    r = _scan({"relation": "replaces", "older_quote": "We chose Acme",
               "newer_quote": "Switched to Ledgerly", "summary": "x"})
    assert r["items"] == []


def test_unknown_relation_or_bad_json_is_ignored(_clean):
    assert _scan({"relation": "delete all files", "older_quote": "We chose Corvid",
                  "newer_quote": "Switched to Ledgerly"})["items"] == []
    assert conflicts.judge("a", "b", "x", "y") is None  # {"relation": ...} missing


def test_forget_and_revoke_clear_findings(_clean):
    _scan({"relation": "contradicts", "older_quote": "We chose Corvid",
           "newer_quote": "Switched to Ledgerly", "summary": "Vendors differ"})
    assert conflicts.report()["items"][0]["kind"] == "conflict"
    permissions.revoke_path(str(_clean))
    assert conflicts.report()["items"] == []
    permissions.allowed_folders.add(_clean.resolve())
    _scan({"relation": "contradicts", "older_quote": "We chose Corvid",
           "newer_quote": "Switched to Ledgerly"})
    session.forget()
    assert conflicts.report() == {"phase": "idle", "done": 0, "total": 0, "items": []}


def test_ollama_down_reports_no_engine(_clean, monkeypatch):
    _scan({"relation": "none"})
    def down(*a, **k):
        raise ConnectionRefusedError
    monkeypatch.setattr(group, "_post", down)
    conflicts._scan(conflicts._gen)
    assert conflicts.status()["phase"] == "no_engine"
