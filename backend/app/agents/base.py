from __future__ import annotations

from typing import Any

from app.services.model_provider import ModelProvider
from app.services.task_models import Task, TaskExecution, TaskResult, TaskStatus, TaskStep


class BaseAgent:
    name = "base"

    def __init__(self, provider: ModelProvider, max_steps: int = 20) -> None:
        self.provider = provider
        self.max_steps = max_steps

    async def observe(self, task: Task) -> dict[str, Any]:
        return {"goal": task.goal, "project_id": task.project_id}

    async def plan(self, task: Task) -> list[str]:
        raise NotImplementedError

    async def run(self, task: Task) -> TaskResult:
        task.status = TaskStatus.PLANNING
        task.plan = await self.plan(task)
        task.steps = [TaskStep(item) for item in task.plan]
        task.status = TaskStatus.EXECUTING
        return TaskResult(task.id, task.status, "Plan created; approval is required before edits.", task.changed_files, task.diff, task.test_results)
