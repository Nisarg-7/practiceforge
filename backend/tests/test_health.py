from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_ok() -> None:
    # Needs Postgres running: docker compose up -d
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_unknown_route_returns_404() -> None:
    assert client.get("/api/v1/does-not-exist").status_code == 404