from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.base import BaseAgent
from app.services.model_provider import ModelProvider
from app.services.task_models import Task


@dataclass
class SpecializedAgent(BaseAgent):
    provider: ModelProvider
    name: str
    system_instructions: str
    max_steps: int = 20

    async def plan(self, task: Task) -> list[str]:
        return [f"{self.name}: inspect task context", f"{self.name}: produce a focused result"]

    async def run_task(self, goal: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Role: {self.name}\nInstructions: {self.system_instructions}\nGoal: {goal}\nContext: {context}"
        response = await self.provider.generate(prompt)
        return {"agent": self.name, "summary": response}


class PlannerAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "planner", "Create a concise implementation plan without changing files.")


class CoderAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "coder", "Propose focused code changes; never apply edits directly.")


class ReviewerAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "reviewer", "Review proposed changes for correctness, scope, and regressions.")


class DebuggerAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "debugger", "Analyze failures and recommend the smallest safe fix.")


class TesterAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "tester", "Identify and evaluate relevant tests; do not hide failures.")


class SecurityAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "security", "Check for secrets, unsafe operations, and permission violations.")


class GitAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "git", "Inspect repository state and summarize safe Git actions.")


class BrowserAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "browser", "Plan browser verification steps without accessing credentials.")


class ResearcherAgent(SpecializedAgent):
    def __init__(self, provider: ModelProvider) -> None:
        super().__init__(provider, "researcher", "Summarize only the supplied project context and task information.")


def build_agents(provider: ModelProvider) -> dict[str, SpecializedAgent]:
    agents = [PlannerAgent(provider), CoderAgent(provider), ReviewerAgent(provider), DebuggerAgent(provider), TesterAgent(provider), SecurityAgent(provider), GitAgent(provider), BrowserAgent(provider), ResearcherAgent(provider)]
    return {agent.name: agent for agent in agents}
