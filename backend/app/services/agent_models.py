from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class AgentStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class AgentMemory:
    system_instructions: str
    project_context: dict[str, Any] = field(default_factory=dict)
    task_context: dict[str, Any] = field(default_factory=dict)
    tool_permissions: set[str] = field(default_factory=set)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    execution_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentTask:
    name: str
    agent: str
    goal: str
    dependencies: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    status: AgentStatus = AgentStatus.IDLE
    current_action: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    duration: float = 0.0
    retries: int = 0
    memory: AgentMemory | None = None


@dataclass
class AgentRun:
    id: str = field(default_factory=lambda: str(uuid4()))
    tasks: dict[str, AgentTask] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE
    cancelled: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "tasks": [
                {**task.__dict__, "status": task.status, "memory": None}
                for task in self.tasks.values()
            ],
        }
