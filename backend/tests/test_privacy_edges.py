"""Privacy and trust checks that don't need the index yet (tasks 4b, 4c, 4e).
When db.py lands, add: forget empties the index; revoke drops real chunks."""
import os

import pytest
from fastapi.testclient import TestClient

from app import audit, permissions, prefs, session
from app.config import Settings
from app.main import create_app

TOKEN = "s" * 48
AUTH = {"Authorization": f"Bearer {TOKEN}"}
SECRET = "we are dropping Corvid"


@pytest.fixture(autouse=True)
def clean():
    permissions.allowed_folders.clear()
    permissions._revoke_hooks.clear()
    audit.clear()
    yield
    permissions.allowed_folders.clear()
    permissions._revoke_hooks.clear()
    audit.clear()


@pytest.fixture
def notes(tmp_path):
    d = tmp_path / "notes"
    d.mkdir()
    (d / "a.md").write_text(SECRET)
    return d


def client() -> TestClient:
    return TestClient(create_app(Settings(port=0, session_token=TOKEN)))


# 4c: forget everything -----------------------------------------------------

def test_forget_clears_grants_prefs_and_log(notes):
    c = client()
    c.post("/api/folders", json={"path": str(notes)}, headers=AUTH)
    assert prefs.path().exists()
    body = c.delete("/api/session", headers=AUTH).json()
    assert permissions.allowed_folders == set()
    assert not prefs.path().exists()
    assert [e["action"] for e in audit.entries()] == ["forget"]
    assert body["cleared"]["folders"] == 1
    assert c.get("/api/folders", headers=AUTH).json() == {"paths": []}


def test_forget_twice_is_safe():
    session.forget()
    session.forget()
    assert not prefs.path().exists()


# 4b: revoke drops chunks (stub until db.py) --------------------------------

def test_revoke_calls_drop_hooks_with_resolved_path(notes):
    calls = []
    permissions.on_revoke("index", lambda p: calls.append(p) or 3)
    permissions.grant_path(str(notes))
    permissions.revoke_path(str(notes / ".." / "notes"))
    assert calls == [notes.resolve()]
    assert audit.entries()[-1]["outcome"] == "ok; index: 3 dropped"


def test_revoke_of_unknown_path_drops_nothing(notes):
    calls = []
    permissions.on_revoke("index", calls.append)
    permissions.revoke_path(str(notes))
    assert calls == []


# 4e: edge cases --------------------------------------------------------------

def test_symlink_into_denied_folder_is_refused(tmp_path, notes):
    ssh = tmp_path / ".ssh"
    ssh.mkdir()
    (ssh / "id_rsa").write_text("key")
    os.symlink(ssh, notes / "link")
    permissions.grant_path(str(notes))
    with pytest.raises(PermissionError):
        permissions.resolve_and_check(str(notes / "link" / "id_rsa"))
    with pytest.raises(PermissionError):
        permissions.grant_path(str(notes / "link"))


def test_symlink_out_of_allowed_folder_is_refused(tmp_path, notes):
    outside = tmp_path / "outside.md"
    outside.write_text("x")
    os.symlink(outside, notes / "sneaky.md")
    permissions.grant_path(str(notes))
    with pytest.raises(PermissionError):
        permissions.resolve_and_check(str(notes / "sneaky.md"))


def test_saved_folder_deleted_between_launches(notes):
    permissions.grant_path(str(notes))
    prefs.save_folders()
    permissions.allowed_folders.clear()
    (notes / "a.md").unlink()
    notes.rmdir()
    assert prefs.restore_folders() == [str(notes.resolve())]
    assert prefs.load()["folders"] == []
    assert audit.entries()[-1]["outcome"] == "missing or blocked on launch"


def test_add_missing_folder_is_404(tmp_path):
    r = client().post("/api/folders", json={"path": str(tmp_path / "nope")}, headers=AUTH)
    assert r.status_code == 404


def test_audit_and_prefs_never_hold_note_text(notes):
    c = client()
    c.post("/api/folders", json={"path": str(notes)}, headers=AUTH)
    c.delete("/api/folders", params={"path": str(notes)}, headers=AUTH)
    assert SECRET not in str(audit.entries())
    assert SECRET not in prefs.path().read_text()
