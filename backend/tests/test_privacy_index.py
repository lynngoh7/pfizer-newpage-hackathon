"""Tasks 4b, 4c, 2e against the real index: revoke and forget through the API,
revoke/forget while a rebuild is embedding, and unloading the model."""
import io
import json
import urllib.request

import pytest
from fastapi.testclient import TestClient

from app import audit, db, group, ingest, models, permissions, session
from app.config import Settings
from app.main import create_app

TOKEN = "p" * 48
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def notes(tmp_path):
    permissions.on_revoke("index", db.drop_under)  # test_privacy_edges clears hooks
    session.on_forget("index", db.clear)
    session.on_forget("model", models.unload)
    d = tmp_path / "notes"
    d.mkdir()
    (d / "vendor.md").write_text("# Decision\nWe chose Acme as the vendor.\n")
    (d / "budget.md").write_text("# Budget\nReduced funding for Q4.\n")
    db.clear(); audit.clear(); permissions.allowed_folders.clear()
    yield d
    db.clear(); ingest.chunks.clear(); permissions.allowed_folders.clear()


def client():
    return TestClient(create_app(Settings(port=0, session_token=TOKEN)))


def fake_ollama(monkeypatch, loaded):
    """Stand-in Ollama: embeds, names groups, reports `loaded`, records calls."""
    calls = []

    def post(path, body):
        calls.append((path, body))
        if path == "/api/embed" and body.get("input"):
            return {"embeddings": [[1.0, 0.0] for _ in body["input"]]}
        return {"response": json.dumps({"topic": "Vendor"})}

    def urlopen(url, timeout=None):
        return io.BytesIO(json.dumps({"models": [{"name": n} for n in loaded]}).encode())

    monkeypatch.setattr(group, "_post", post)
    monkeypatch.setattr(models, "_post", post)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return calls


def search(c, q):
    return c.get("/api/search", params={"q": q}, headers=AUTH).json()["sources"]


# 4b ------------------------------------------------------------------------

def test_revoke_through_api_drops_chunks_and_results(notes, monkeypatch):
    fake_ollama(monkeypatch, [])
    c = client()
    c.post("/api/folders", json={"path": str(notes)}, headers=AUTH)
    c.post("/api/index", headers=AUTH)
    assert search(c, "Acme")
    c.delete("/api/folders", params={"path": str(notes)}, headers=AUTH)
    assert search(c, "Acme") == []
    assert db.stats()["chunks"] == db.stats()["vectors"] == 0
    removed = [e for e in audit.entries() if e["action"] == "folder_removed"]
    assert "index: 2 dropped" in removed[-1]["outcome"]


def test_revoke_during_build_keeps_no_vectors_or_topics(notes, monkeypatch):
    fake_ollama(monkeypatch, [])
    real_embed = group.embed

    def embed_then_revoke(chunks):
        vecs = real_embed(chunks)
        permissions.revoke_path(str(notes))  # user revokes while embedding runs
        return vecs

    monkeypatch.setattr(group, "embed", embed_then_revoke)
    permissions.grant_path(str(notes))
    client().post("/api/index", headers=AUTH)
    assert db.stats() == {**db.stats(), "chunks": 0, "vectors": 0, "groups": 0}
    assert ingest.chunks == []


# 4c ------------------------------------------------------------------------

def test_forget_through_api_empties_index_and_unloads_model(notes, monkeypatch):
    calls = fake_ollama(monkeypatch, ["nomic-embed-text:latest", "llama3.2:3b"])
    c = client()
    c.post("/api/folders", json={"path": str(notes)}, headers=AUTH)
    c.post("/api/index", headers=AUTH)
    calls.clear()
    cleared = c.delete("/api/session", headers=AUTH).json()["cleared"]
    assert cleared["index"] == 2 and cleared["model"] == 2
    assert {p for p, b in calls if b.get("keep_alive") == 0} == {"/api/embed", "/api/generate"}
    assert db.stats()["chunks"] == 0 and search(c, "Acme") == []


def test_forget_during_build_keeps_no_vectors_or_topics(notes, monkeypatch):
    fake_ollama(monkeypatch, [])
    real_embed = group.embed

    def embed_then_forget(chunks):
        vecs = real_embed(chunks)
        session.forget()
        return vecs

    monkeypatch.setattr(group, "embed", embed_then_forget)
    permissions.grant_path(str(notes))
    client().post("/api/index", headers=AUTH)
    assert db.stats() == {**db.stats(), "chunks": 0, "vectors": 0, "groups": 0}


# 2e ------------------------------------------------------------------------

def test_unload_skips_models_that_are_not_loaded(monkeypatch):
    calls = fake_ollama(monkeypatch, ["some-other-model:7b"])
    assert models.unload() == 0 and calls == []


def test_unload_with_ollama_off_is_safe():
    assert models.unload() == 0  # conftest points Ollama at a closed port


def test_unload_route_needs_token(monkeypatch):
    fake_ollama(monkeypatch, ["llama3.2:3b"])
    c = client()
    assert c.post("/api/engine/unload").status_code == 401
    assert c.post("/api/engine/unload", headers=AUTH).json() == {"unloaded": 1}
