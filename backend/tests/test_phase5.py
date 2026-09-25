import asyncio

import pytest

from app.services.agent_models import AgentStatus
from app.services.agent_orchestrator import AgentOrchestrator


class FakeProvider:
    async def generate(self, prompt: str, model: str | None = None) -> str:
        await asyncio.sleep(0)
        return "ok"

    async def stream(self, prompt: str, model: str | None = None):
        yield "ok"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["test"]


@pytest.mark.anyio
async def test_sequential_and_parallel_dependencies() -> None:
    orchestrator = AgentOrchestrator(FakeProvider())
    run = orchestrator.create_run("build feature", [
        {"name": "plan", "agent": "planner", "goal": "plan"},
        {"name": "code", "agent": "coder", "goal": "code", "dependencies": ["plan"]},
        {"name": "security", "agent": "security", "goal": "scan", "dependencies": ["plan"]},
        {"name": "review", "agent": "reviewer", "goal": "review", "dependencies": ["code", "security"]},
    ])
    await orchestrator.execute(run)
    assert run.status == AgentStatus.COMPLETED
    assert all(task.status == AgentStatus.COMPLETED for task in run.tasks.values())


@pytest.mark.anyio
async def test_failed_agent_retries_and_fails() -> None:
    class FailingProvider(FakeProvider):
        async def generate(self, prompt: str, model: str | None = None) -> str:
            raise RuntimeError("provider failure")

    orchestrator = AgentOrchestrator(FailingProvider(), max_retries=1)
    run = orchestrator.create_run("fail", [{"name": "plan", "agent": "planner", "goal": "fail"}])
    await orchestrator.execute(run)
    assert run.status == AgentStatus.FAILED
    assert run.tasks["plan"].retries == 2


def test_dependency_cycle_is_rejected() -> None:
    with pytest.raises(ValueError, match="cycle"):
        AgentOrchestrator(FakeProvider()).create_run("cycle", [
            {"name": "a", "agent": "planner", "goal": "a", "dependencies": ["b"]},
            {"name": "b", "agent": "coder", "goal": "b", "dependencies": ["a"]},
        ])
