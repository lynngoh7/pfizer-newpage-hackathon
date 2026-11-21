"""Task 4d (part): the app never reaches off the machine (brief §6 "No network").

Every socket connect and DNS lookup to a non-loopback address raises, then a
whole session runs through the real API. Any outbound call fails the test.
Indexing, search and model unload are covered; add the ask call when 2c lands."""
import ipaddress
import socket

import pytest
from fastapi.testclient import TestClient

from app import audit, db, group, permissions, session
from app.config import Settings
from app.main import create_app

TOKEN = "s" * 48
AUTH = {"Authorization": f"Bearer {TOKEN}"}
LOCAL_NAMES = {"localhost", "127.0.0.1", "::1", "testserver"}


def _is_local(host) -> bool:
    if host is None or host in LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    attempts = []
    real_connect, real_lookup = socket.socket.connect, socket.getaddrinfo

    def connect(self, address):
        host = address[0] if isinstance(address, tuple) else None  # unix sockets have no host
        if not _is_local(host):
            attempts.append(address)
            raise OSError(f"blocked outbound connect to {address}")
        return real_connect(self, address)

    def lookup(host, *args, **kwargs):
        if not _is_local(host):
            attempts.append(host)
            raise socket.gaierror(f"blocked DNS lookup for {host}")
        return real_lookup(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    permissions.allowed_folders.clear()
    yield attempts
    permissions.allowed_folders.clear()
    audit.clear()
    assert attempts == [], f"app tried to reach off the machine: {attempts}"


def test_the_guard_catches_outbound_calls(offline):
    with pytest.raises(OSError):
        socket.create_connection(("example.com", 443), timeout=1)
    assert offline == ["example.com"]
    offline.clear()  # expected attempt; keep the fixture's final check clean


def test_ollama_address_is_loopback_only():
    # conftest moves the port for tests; the host must stay loopback
    host = group.OLLAMA.split("//")[1].split(":")[0]
    assert ipaddress.ip_address(host).is_loopback


def test_full_session_stays_on_the_machine(tmp_path):
    permissions.on_revoke("index", db.drop_under)  # test_privacy_edges clears hooks
    session.on_forget("index", db.clear)
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "a.md").write_text("Link: https://example.com/budget, never fetched")
    c = TestClient(create_app(Settings(port=0, session_token=TOKEN)))
    for method, url, kw in [
        ("get", "/api/health", {}),
        ("post", "/api/folders", {"json": {"path": str(notes)}}),
        ("get", "/api/folders", {}),
        ("post", "/api/index", {}),
        ("get", "/api/index", {}),
        ("get", "/api/search", {"params": {"q": "budget example.com"}}),
        ("post", "/api/engine/unload", {}),
        ("put", "/api/settings", {"json": {}}),
        ("get", "/api/audit", {}),
        ("get", "/api/trust/network", {}),
        ("get", "/api/trust/saved", {}),
        ("get", "/api/trust/storage", {}),
        ("delete", "/api/folders", {"params": {"path": str(notes)}}),
        ("delete", "/api/session", {}),
    ]:
        r = getattr(c, method)(url, headers=AUTH, **kw)
        assert r.status_code < 500, (url, r.status_code)
    db.clear()
