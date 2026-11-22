"""Capture: open in editor (path-enforced, never edits) and new notes (never overwrite)."""
import pytest
from fastapi.testclient import TestClient

from app import audit, notes, permissions, search
from app.config import Settings
from app.main import create_app

TOKEN = "n" * 48
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    permissions.allowed_folders.clear()
    audit.clear()
    launched = []
    monkeypatch.setattr(notes, "_launch", launched.append)
    monkeypatch.setattr(search, "reindex", lambda *a, **k: {})
    yield launched
    permissions.allowed_folders.clear()


def client() -> TestClient:
    return TestClient(create_app(Settings(port=0, session_token=TOKEN)))


def test_open_allowed_file(tmp_path, clean):
    note = tmp_path / "a.md"
    note.write_text("x")
    permissions.grant_path(str(tmp_path))
    r = client().post("/api/files/open", json={"path": str(note)}, headers=HEADERS)
    assert r.status_code == 200
    assert clean == [note.resolve()]


def test_open_outside_allowlist_refused(tmp_path, clean):
    note = tmp_path / "a.md"
    note.write_text("x")
    r = client().post("/api/files/open", json={"path": str(note)}, headers=HEADERS)
    assert r.status_code == 403
    assert clean == []


def test_open_denylisted_refused(tmp_path, clean):
    secret = tmp_path / ".ssh" / "id"
    secret.parent.mkdir()
    secret.write_text("k")
    permissions.allowed_folders.add(tmp_path.resolve())
    r = client().post("/api/files/open", json={"path": str(secret)}, headers=HEADERS)
    assert r.status_code == 403
    assert clean == []


def test_create_tracked_note_and_no_content_in_audit(tmp_path):
    permissions.grant_path(str(tmp_path))
    r = client().post("/api/notes", json={"folder": str(tmp_path), "title": "Budget idea",
                                          "body": "secret thought"}, headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["tracked"] is True
    assert "secret thought" in open(data["path"]).read()
    assert "secret thought" not in str(audit.entries())


def test_create_untracked_and_never_overwrites(tmp_path):
    body = {"folder": str(tmp_path), "title": "Same", "body": "one"}
    first = client().post("/api/notes", json=body, headers=HEADERS).json()
    second = client().post("/api/notes", json={**body, "body": "two"}, headers=HEADERS).json()
    assert first["tracked"] is False
    assert first["path"] != second["path"]
    assert "one" in open(first["path"]).read()


def test_create_in_denylisted_folder_refused(tmp_path):
    bad = tmp_path / ".ssh"
    bad.mkdir()
    r = client().post("/api/notes", json={"folder": str(bad), "body": "x"}, headers=HEADERS)
    assert r.status_code == 403
    assert list(bad.iterdir()) == []


def test_title_cannot_escape_folder(tmp_path):
    data = client().post("/api/notes", json={"folder": str(tmp_path), "title": "../../evil",
                                             "body": "x"}, headers=HEADERS).json()
    assert str(tmp_path.resolve()) in data["path"]
