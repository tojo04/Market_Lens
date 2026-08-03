from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_typed_status() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MarketLens AI API",
    }
    assert response.headers["X-Request-ID"]


def test_health_endpoint_preserves_supplied_request_id() -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "phase-0-check"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "phase-0-check"
