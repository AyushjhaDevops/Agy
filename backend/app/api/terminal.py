from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.terminal_service import CommandApprovalRequired, CommandExecutor, ExecutionPolicy

router = APIRouter(prefix="/api/v1/terminal", tags=["terminal"])
_sessions: dict[str, CommandExecutor] = {}
_history: dict[str, list[dict]] = {}


class CommandRequest(BaseModel):
    command: str = Field(min_length=1)
    cwd: str | None = None
    approved: bool = False
    policy: ExecutionPolicy = ExecutionPolicy.RESTRICTED
    timeout: float = Field(default=120, gt=0, le=600)


def executor(settings: Settings = Depends(get_settings)) -> CommandExecutor:
    return CommandExecutor(settings.projects_root, ExecutionPolicy.RESTRICTED)


@router.get("/policies")
def policies() -> dict:
    return {"policies": [item.value for item in ExecutionPolicy], "os_isolation": False}


@router.post("/execute")
async def execute(request: CommandRequest, settings: Settings = Depends(get_settings)) -> dict:
    execution_id = str(uuid4())
    runner = CommandExecutor(settings.projects_root, request.policy)
    _sessions[execution_id] = runner
    try:
        result = await runner.execute(request.command, request.cwd, request.approved, request.timeout, execution_id)
    except CommandApprovalRequired as exc:
        raise HTTPException(status_code=428, detail=str(exc)) from exc
    except (PermissionError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    finally:
        _history.setdefault("default", []).append({"id": execution_id, "command": request.command, "cwd": request.cwd, "status": "completed"})
    return {"id": execution_id, **result.__dict__}


@router.post("/{execution_id}/stop")
async def stop(execution_id: str) -> dict:
    runner = _sessions.get(execution_id)
    if not runner: raise HTTPException(status_code=404, detail="Execution not found")
    return {"id": execution_id, "cancelled": await runner.cancel(execution_id)}


@router.get("/history")
def history() -> dict:
    return {"history": _history.get("default", [])[-100:]}
