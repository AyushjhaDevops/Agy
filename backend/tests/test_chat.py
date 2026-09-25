from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_provider, get_store
from app.main import app
from app.services.model_provider import ModelNotFoundError, ProviderUnavailableError


class FakeProvider:
    default_model = "test-model"

    async def generate(self, prompt: str, model: str | None = None) -> str:
        return "Generated response"

    async def stream(self, prompt: str, model: str | None = None):
        yield "Generated "
        yield "response"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["test-model"]


@pytest.fixture
def client(tmp_path: Path):
    class Settings:
        database_url = f"sqlite:///{tmp_path / 'test.db'}"
        ollama_base_url = "http://ollama.test"
        ollama_model = "test-model"
        ollama_timeout_seconds = 1.0

    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    app.dependency_overrides[get_store] = lambda: __import__("app.services.conversation_store", fromlist=["ConversationStore"]).ConversationStore(Settings.database_url)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_chat_generation_and_persistence(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "Hello"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Generated response"
    assert payload["status"] == "completed"
    conversation_id = payload["conversation_id"]

    second = client.post("/api/v1/chat", json={"message": "Again", "conversation_id": conversation_id})
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id


def test_streaming_chat(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/chat/stream") as websocket:
        websocket.send_json({"message": "Stream"})
        assert websocket.receive_json()["content"] == "Generated "
        assert websocket.receive_json()["content"] == "response"
        assert websocket.receive_json()["type"] == "done"
