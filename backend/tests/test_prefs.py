import json

import pytest
from fastapi.testclient import TestClient

from app import permissions, prefs, session, trust
from app.config import Settings
from app.main import create_app

TOKEN = "s" * 48
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def clean():
    permissions.allowed_folders.clear()
    yield
    permissions.allowed_folders.clear()


def client() -> TestClient:
    return TestClient(create_app(Settings(port=0, session_token=TOKEN)))


def test_folder_add_and_remove_are_saved(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "a.md").write_text("secret meeting text")
    c = client()
    c.post("/api/folders", json={"path": str(notes)}, headers=AUTH)
    saved = prefs.path().read_text()
    assert str(notes.resolve()) in saved
    assert "secret meeting text" not in saved  # One Rule: paths only
    c.delete("/api/folders", params={"path": str(notes)}, headers=AUTH)
    assert prefs.load()["folders"] == []


def test_restore_regrants_and_drops_missing(tmp_path):
    keep = tmp_path / "keep"
    keep.mkdir()
    prefs._write({"folders": [str(keep), str(tmp_path / "gone")], "settings": {}})
    assert prefs.restore_folders() == [str(tmp_path / "gone")]
    assert permissions.list_allowed_paths() == [keep.resolve()]
    assert prefs.load()["folders"] == [str(keep.resolve())]


def test_only_allowlisted_settings_are_saved():
    prefs.save_settings({"answer_model": "llama3.2:3b", "notes": "copied text", "answer_model2": 1})
    assert json.loads(prefs.path().read_text())["settings"] == {"answer_model": "llama3.2:3b"}
    c = client()
    assert c.put("/api/settings", json={"answer_model": "x" * 101}, headers=AUTH).json() == {"answer_model": "llama3.2:3b"}
    assert c.get("/api/settings", headers=AUTH).json() == {"answer_model": "llama3.2:3b"}


def test_broken_file_loads_empty():
    prefs.path().parent.mkdir(parents=True)
    prefs.path().write_text("{not json")
    assert prefs.load() == {"folders": [], "settings": {}}


def test_storage_does_not_flag_prefs_but_flags_others(monkeypatch):
    prefs.save_settings({"answer_model": "m"})
    monkeypatch.setattr(trust, "_app_dirs", lambda: [prefs.path().parent])
    report = trust.storage()
    assert report["files"] == 0 and report["saved"]["bytes"] > 0
    (prefs.path().parent / "cache.db").write_bytes(b"x")
    assert trust.storage()["files"] == 1


def test_forget_deletes_file_and_grants(tmp_path):
    permissions.grant_path(str(tmp_path))
    prefs.save_folders()
    cleared = session.forget()
    assert cleared["folders"] == 1
    assert not prefs.path().exists()
    assert permissions.list_allowed_paths() == []
