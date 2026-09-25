from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    TESTING = "TESTING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskStep:
    name: str
    status: str = "pending"
    tool: str | None = None
    result: dict[str, Any] | None = None


@dataclass
class Task:
    goal: str
    project_id: str = "current"
    id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    plan: list[str] = field(default_factory=list)
    steps: list[TaskStep] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    diff: str = ""
    test_results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class TaskExecution:
    task_id: str
    current_step: int = 0
    max_steps: int = 20
    approved: bool = False


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    summary: str
    changed_files: list[str]
    diff: str
    test_results: list[dict[str, Any]]
