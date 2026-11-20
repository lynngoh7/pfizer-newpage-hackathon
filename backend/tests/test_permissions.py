import pytest
from fastapi.testclient import TestClient

from app import permissions
from app.config import Settings
from app.main import create_app

TOKEN = "p" * 48
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def clear_allowed_paths():
    permissions.allowed_folders.clear()
    yield
    permissions.allowed_folders.clear()


def client() -> TestClient:
    return TestClient(create_app(Settings(port=0, session_token=TOKEN)))


def test_folder_grant_allows_descendants(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("meeting notes")

    granted = permissions.grant_path(str(tmp_path))

    assert permissions.resolve_and_check(str(note)) == note.resolve()
    assert granted == tmp_path.resolve()


def test_file_grant_only_allows_the_selected_file(tmp_path):
    selected = tmp_path / "selected.md"
    other = tmp_path / "other.md"
    selected.touch()
    other.touch()
    permissions.grant_path(str(selected))

    assert permissions.resolve_and_check(str(selected)) == selected.resolve()
    with pytest.raises(PermissionError, match="Outside allowed folders"):
        permissions.resolve_and_check(str(other))


def test_symlink_cannot_escape_an_allowed_folder(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    private = tmp_path / "private.md"
    private.touch()
    link = allowed / "shortcut.md"
    link.symlink_to(private)
    permissions.grant_path(str(allowed))

    with pytest.raises(PermissionError, match="Outside allowed folders"):
        permissions.resolve_and_check(str(link))


def test_blocked_location_cannot_be_granted(tmp_path):
    blocked = tmp_path / ".ssh"
    blocked.mkdir()

    with pytest.raises(PermissionError, match="Blocked location"):
        permissions.grant_path(str(blocked))


def test_folder_access_routes_add_list_and_revoke(tmp_path):
    selected = tmp_path / "notes"
    selected.mkdir()
    api = client()

    response = api.post("/api/folders", headers=HEADERS, json={"path": str(selected)})
    assert response.status_code == 200
    assert response.json()["paths"] == [str(selected.resolve())]
    assert api.get("/api/folders", headers=HEADERS).json()["paths"] == [str(selected.resolve())]

    response = api.delete(
        "/api/folders",
        headers=HEADERS,
        params={"path": str(selected.resolve())},
    )
    assert response.status_code == 200
    assert response.json()["paths"] == []


def test_folder_access_rejects_missing_and_blocked_paths(tmp_path):
    api = client()
    missing = api.post(
        "/api/folders",
        headers=HEADERS,
        json={"path": str(tmp_path / "missing")},
    )
    assert missing.status_code == 404

    blocked = tmp_path / ".ssh"
    blocked.mkdir()
    response = api.post("/api/folders", headers=HEADERS, json={"path": str(blocked)})
    assert response.status_code == 403


def test_folder_events_are_audited_without_content(tmp_path):
    from app import audit, permissions
    audit.clear()
    permissions.grant_path(str(tmp_path))
    permissions.revoke_path(str(tmp_path))
    permissions.revoke_path(str(tmp_path))  # not granted any more: no second line
    blocked = tmp_path / ".ssh"
    blocked.mkdir()
    with pytest.raises(PermissionError):
        permissions.grant_path(str(blocked))
    log = [(e["action"], e["path"]) for e in audit.entries()]
    assert log == [
        ("folder_added", str(tmp_path.resolve())),
        ("folder_removed", str(tmp_path.resolve())),
        ("blocked", str(blocked)),
    ]
    audit.clear()
