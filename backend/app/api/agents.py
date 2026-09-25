from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.model_provider import ModelProvider
from app.services.ollama_service import OllamaProvider

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
_orchestrators: dict[str, AgentOrchestrator] = {}


class AgentTaskRequest(BaseModel):
    name: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    dependencies: list[str] = []


class AgentRunRequest(BaseModel):
    goal: str = Field(min_length=1)
    tasks: list[AgentTaskRequest] = Field(min_length=1)


def get_provider(settings: Settings = Depends(get_settings)) -> OllamaProvider:
    return OllamaProvider(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_seconds)


@router.get("")
def agent_catalog() -> dict[str, list[str]]:
    return {"agents": ["planner", "coder", "reviewer", "debugger", "tester", "security", "git", "browser", "researcher"]}


@router.post("/runs")
async def create_run(request: AgentRunRequest, provider: ModelProvider = Depends(get_provider)) -> dict:
    orchestrator = AgentOrchestrator(provider)
    try:
        run = orchestrator.create_run(request.goal, [task.model_dump() for task in request.tasks])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _orchestrators[run.id] = orchestrator
    await orchestrator.execute(run)
    return run.as_dict()


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    orchestrator = _orchestrators.get(run_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return orchestrator.runs[run_id].as_dict()


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict:
    orchestrator = _orchestrators.get(run_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return orchestrator.cancel(run_id).as_dict()
