from fastapi.testclient import TestClient

from app.main import app


def test_healthz_ok() -> None:
    client = TestClient(app)
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_legacy_chat_route_removed() -> None:
    client = TestClient(app)
    res = client.post("/api/v1/chat/message", json={"session_id": str(__import__("uuid").uuid4()), "message": "x"})
    assert res.status_code == 404


def test_delete_unknown_session_returns_404() -> None:
    client = TestClient(app)
    res = client.delete(f"/api/v1/sessions/{__import__('uuid').uuid4()}")
    assert res.status_code == 404

