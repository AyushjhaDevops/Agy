from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from typing import Any

from app.agents.specialized import build_agents
from app.services.agent_models import AgentMemory, AgentRun, AgentStatus, AgentTask
from app.services.model_provider import ModelProvider


class AgentOrchestrator:
    """Dependency-aware async scheduler with bounded retries and cancellation."""

    def __init__(self, provider: ModelProvider, max_retries: int = 1) -> None:
        self.provider = provider
        self.max_retries = max_retries
        self.agents = build_agents(provider)
        self.runs: dict[str, AgentRun] = {}

    def create_run(self, goal: str, task_specs: Iterable[dict[str, Any]]) -> AgentRun:
        run = AgentRun()
        for spec in task_specs:
            task = AgentTask(
                name=spec["name"], agent=spec["agent"], goal=spec.get("goal", goal),
                dependencies=list(spec.get("dependencies", [])),
                memory=AgentMemory(system_instructions=self.agents[spec["agent"]].system_instructions),
            )
            if task.agent not in self.agents:
                raise ValueError(f"Unknown agent: {task.agent}")
            run.tasks[task.name] = task
        self._validate_graph(run)
        self.runs[run.id] = run
        return run

    def _validate_graph(self, run: AgentRun) -> None:
        for task in run.tasks.values():
            missing = set(task.dependencies) - run.tasks.keys()
            if missing:
                raise ValueError(f"Missing task dependencies: {sorted(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError("Task dependency cycle detected")
            if name in visited:
                return
            visiting.add(name)
            for dependency in run.tasks[name].dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in run.tasks:
            visit(name)

    async def execute(self, run: AgentRun) -> AgentRun:
        run.status = AgentStatus.RUNNING
        while not run.cancelled:
            ready = [task for task in run.tasks.values() if task.status == AgentStatus.IDLE and all(run.tasks[name].status == AgentStatus.COMPLETED for name in task.dependencies)]
            if not ready:
                pending = [task for task in run.tasks.values() if task.status in {AgentStatus.IDLE, AgentStatus.RUNNING, AgentStatus.WAITING}]
                if pending:
                    run.status = AgentStatus.FAILED
                    for task in pending:
                        task.status, task.error = AgentStatus.FAILED, "Dependency failed"
                break
            await asyncio.gather(*(self._execute_task(run, task) for task in ready))
            if any(task.status == AgentStatus.FAILED for task in run.tasks.values()):
                run.status = AgentStatus.FAILED
                break
        if run.cancelled:
            run.status = AgentStatus.CANCELLED
            for task in run.tasks.values():
                if task.status in {AgentStatus.IDLE, AgentStatus.WAITING, AgentStatus.RUNNING}:
                    task.status = AgentStatus.CANCELLED
        elif all(task.status == AgentStatus.COMPLETED for task in run.tasks.values()):
            run.status = AgentStatus.COMPLETED
        return run

    async def _execute_task(self, run: AgentRun, task: AgentTask) -> None:
        task.status, task.current_action = AgentStatus.RUNNING, "executing"
        started = time.perf_counter()
        agent = self.agents[task.agent]
        context = {name: run.tasks[name].result for name in task.dependencies}
        try:
            task.result = await agent.run_task(task.goal, context)
            task.status, task.current_action = AgentStatus.COMPLETED, "completed"
        except asyncio.CancelledError:
            task.status = AgentStatus.CANCELLED
            raise
        except Exception as exc:
            task.retries += 1
            if task.retries <= self.max_retries and not run.cancelled:
                task.status, task.current_action = AgentStatus.WAITING, "retrying"
                await self._execute_task(run, task)
                return
            task.status, task.error, task.current_action = AgentStatus.FAILED, str(exc), "failed"
        finally:
            task.duration = time.perf_counter() - started

    def cancel(self, run_id: str) -> AgentRun:
        run = self.runs[run_id]
        run.cancelled = True
        return run
