from __future__ import annotations

from app.services.context_engine import ContextEngine
from app.services.model_provider import ModelProvider
from app.services.project_indexer import ProjectIndexer
from app.services.task_models import Task, TaskResult, TaskStatus
from app.tools.filesystem import PatchTool


class PlannerAgent:
    name = "planner"

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    async def plan(self, task: Task, context: list[dict]) -> list[str]:
        return ["Inspect relevant repository files", "Prepare a focused patch", "Review the diff", "Run tests", "Report results"]


class CodingAgent:
    name = "coder"

    def __init__(self, provider: ModelProvider, indexer: ProjectIndexer, max_steps: int = 20) -> None:
        self.provider, self.indexer, self.max_steps = provider, indexer, max_steps
        self.planner = PlannerAgent(provider)
        self.patch_tools: dict[str, PatchTool] = {}

    async def plan(self, task: Task) -> Task:
        project = self.indexer.resolve(task.project_id)
        context = ContextEngine(self.indexer).select(project, task.goal)
        task.plan = await self.planner.plan(task, context)
        task.steps = [__import__("app.services.task_models", fromlist=["TaskStep"]).TaskStep(item) for item in task.plan]
        task.status = TaskStatus.PLANNING
        task.error = None
        return task

    def propose_patch(self, task: Task, path: str, new_content: str) -> dict:
        project = self.indexer.resolve(task.project_id)
        tool = self.patch_tools.setdefault(task.id, PatchTool(project))
        result = tool.execute(path=path, new_content=new_content, approved=False)
        task.diff = result["diff"]
        if path not in task.changed_files:
            task.changed_files.append(path)
        return result

    def apply_patch(self, task: Task, path: str, new_content: str) -> dict:
        project = self.indexer.resolve(task.project_id)
        tool = self.patch_tools.setdefault(task.id, PatchTool(project))
        result = tool.execute(path=path, new_content=new_content, approved=True)
        task.status = TaskStatus.EXECUTING
        return result

    def rollback(self, task: Task, path: str) -> None:
        self.patch_tools.get(task.id, PatchTool(self.indexer.resolve(task.project_id))).rollback(path)


class TestAgent:
    name = "tester"

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider


class DebuggerAgent:
    name = "debugger"

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider


class AgentManager:
    def __init__(self, provider: ModelProvider, indexer: ProjectIndexer) -> None:
        self.coder = CodingAgent(provider, indexer)
        self.planner = PlannerAgent(provider)
        self.test = TestAgent(provider)
        self.debugger = DebuggerAgent(provider)
