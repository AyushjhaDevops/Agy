from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.api.projects import get_indexer
from app.api.tasks import get_provider


class FakeProvider:
    default_model = "test"

    async def generate(self, prompt: str, model: str | None = None) -> str:
        return "ok"

    async def stream(self, prompt: str, model: str | None = None):
        yield "ok"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["test"]


def test_task_plans_and_requires_proposal(tmp_path: Path):
    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    app.dependency_overrides[get_indexer] = lambda: __import__("app.services.project_indexer", fromlist=["ProjectIndexer"]).ProjectIndexer(str(tmp_path))
    client = TestClient(app)
    response = client.post("/api/v1/tasks", json={"goal": "Add users endpoint"})
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "PLANNING"
    assert task["plan"]
    app.dependency_overrides.clear()


def test_patch_tool_is_diff_first(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("old\n", encoding="utf-8")
    from app.services.project_indexer import ProjectIndexer
    from app.tools.filesystem import PatchTool
    result = PatchTool(ProjectIndexer(str(tmp_path)).resolve("current")).execute(path="app.py", new_content="new\n", approved=False)
    assert result["applied"] is False
    assert path.read_text(encoding="utf-8") == "old\n"
