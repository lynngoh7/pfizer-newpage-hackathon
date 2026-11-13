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
