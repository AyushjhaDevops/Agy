from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.projects import get_indexer
from app.core.config import Settings, get_settings
from app.services.model_provider import ModelProvider
from app.services.ollama_service import OllamaProvider
from app.services.task_models import Task, TaskStatus
from app.agents.coding import AgentManager

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
_tasks: dict[str, Task] = {}


class CreateTaskRequest(BaseModel):
    goal: str = Field(min_length=1)
    project_id: str = "current"


class PatchRequest(BaseModel):
    path: str = Field(min_length=1)
    new_content: str


def get_provider(settings: Settings = Depends(get_settings)) -> OllamaProvider:
    return OllamaProvider(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_seconds)


@router.post("")
async def create_task(request: CreateTaskRequest, provider: ModelProvider = Depends(get_provider), indexer=Depends(get_indexer)) -> Task:
    try:
        indexer.resolve(request.project_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    task = Task(goal=request.goal, project_id=request.project_id)
    _tasks[task.id] = task
    await AgentManager(provider, indexer).coder.plan(task)
    return task


@router.get("/{task_id}")
def get_task(task_id: str) -> Task:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[task_id]


@router.post("/{task_id}/propose")
def propose(task_id: str, request: PatchRequest, provider: ModelProvider = Depends(get_provider), indexer=Depends(get_indexer)) -> Task:
    task = get_task(task_id)
    result = AgentManager(provider, indexer).coder.propose_patch(task, request.path, request.new_content)
    task.diff = result["diff"]
    return task


@router.post("/{task_id}/approve")
def approve(task_id: str, request: PatchRequest, provider: ModelProvider = Depends(get_provider), indexer=Depends(get_indexer)) -> Task:
    task = get_task(task_id)
    AgentManager(provider, indexer).coder.apply_patch(task, request.path, request.new_content)
    task.status = TaskStatus.TESTING
    return task


@router.post("/{task_id}/cancel")
def cancel(task_id: str) -> Task:
    task = get_task(task_id)
    task.status = TaskStatus.CANCELLED
    return task
