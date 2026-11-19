from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TOKEN = "t" * 48


def client() -> TestClient:
    return TestClient(create_app(Settings(port=0, session_token=TOKEN)))


def test_health_requires_token():
    assert client().get("/api/health").status_code == 401
    assert client().get("/api/health", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_health_ok_with_token():
    r = client().get("/api/health", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["read_only"] is True
    assert body["network"] == "localhost-only"
    assert r.headers["cache-control"] == "no-store"


def test_browser_dev_origin_only_allowed_in_dev_mode():
    headers = {"Authorization": f"Bearer {TOKEN}", "Origin": "http://127.0.0.1:1420"}
    packaged = TestClient(create_app(Settings(port=0, session_token=TOKEN)))
    assert "access-control-allow-origin" not in packaged.get("/api/health", headers=headers).headers
    dev = TestClient(create_app(Settings(port=0, session_token=TOKEN, dev=True)))
    assert dev.get("/api/health", headers=headers).headers["access-control-allow-origin"] == "http://127.0.0.1:1420"
