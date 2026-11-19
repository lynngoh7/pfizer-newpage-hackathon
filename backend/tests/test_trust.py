from collections import namedtuple

import pytest
from fastapi.testclient import TestClient

from app import audit, session, trust
from app.config import Settings
from app.main import create_app

TOKEN = "t" * 48
AUTH = {"Authorization": f"Bearer {TOKEN}"}
Addr = namedtuple("Addr", "ip port")


@pytest.fixture(autouse=True)
def fresh():
    audit.clear()
    session._resets.clear()
    yield
    audit.clear()
    session._resets.clear()


def client() -> TestClient:
    return TestClient(create_app(Settings(port=0, session_token=TOKEN)))


def test_audit_only_accepts_known_actions_and_short_outcomes():
    with pytest.raises(ValueError):
        audit.record("note text: we are dropping Corvid")
    audit.record("skipped", path="/n/a.pdf", outcome="x" * 500)
    assert len(audit.entries()[0]["outcome"]) == audit.MAX_OUTCOME


def test_audit_polls_by_seq_and_is_bounded():
    audit.record("read", path="/n/a.md")
    last = audit.entries()[-1]["seq"]
    audit.record("read", path="/n/b.md")
    assert [e["path"] for e in audit.entries(after=last)] == ["/n/b.md"]
    for i in range(audit.MAX_ENTRIES + 10):
        audit.record("read", path=f"/n/{i}.md")
    assert len(audit.entries()) == audit.MAX_ENTRIES


def test_forget_runs_every_reset_and_leaves_one_log_line():
    audit.record("read", path="/n/a.md")
    session.on_forget("index", lambda: 42)
    session.on_forget("folders", lambda: 2)
    cleared = session.forget()
    assert cleared == {"index": 42, "folders": 2, "activity_log": 1}
    assert [e["action"] for e in audit.entries()] == ["forget"]


def test_connection_kinds():
    assert trust._kind(None) == "listening"
    assert trust._kind(Addr("127.0.0.1", 11434)) == "local"
    assert trust._kind(Addr("::1", 11434)) == "local"
    assert trust._kind(Addr("10.0.0.5", 443)) == "external"
    assert trust._kind(Addr("93.184.216.34", 443)) == "external"
    assert trust._kind(Addr("not-an-ip", 1)) == "external"


def test_network_report_includes_this_process():
    report = trust.network()
    assert report["processes"][0]["pid"] > 0
    assert isinstance(report["external"], int)


def test_storage_reports_files_in_app_dirs(tmp_path, monkeypatch):
    empty, used = tmp_path / "empty", tmp_path / "used"
    (used / "sub").mkdir(parents=True)
    (used / "sub" / "cache.db").write_bytes(b"1234")
    monkeypatch.setattr(trust, "_app_dirs", lambda: [empty, used])
    report = trust.storage()
    assert report["files"] == 1
    assert report["locations"][0] == {"path": str(empty), "exists": False, "files": 0, "bytes": 0, "listed": []}
    assert report["locations"][1]["listed"] == ["sub/cache.db"]
    assert report["locations"][1]["bytes"] == 4


def test_routes_need_token_and_forget_works(tmp_path, monkeypatch):
    monkeypatch.setattr(trust, "_app_dirs", lambda: [tmp_path / "none"])
    c = client()
    for method, path in [("get", "/api/audit"), ("get", "/api/trust/network"),
                         ("get", "/api/trust/storage"), ("delete", "/api/session")]:
        assert getattr(c, method)(path).status_code == 401
    audit.record("read", path="/n/a.md")
    assert c.get("/api/audit", headers=AUTH).json()[0]["path"] == "/n/a.md"
    body = c.delete("/api/session", headers=AUTH).json()
    assert body["cleared"]["activity_log"] == 1
    assert body["storage"]["files"] == 0
