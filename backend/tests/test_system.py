from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "LocalForge AI"


def test_runtime_config_endpoint() -> None:
    response = client.get("/api/v1/config")

    assert response.status_code == 200
    payload = response.json()

    assert payload["app_name"] == "LocalForge AI"
    assert payload["ollama_model"]
    assert "api_key" not in payload
