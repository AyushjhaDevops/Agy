from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.browser_service import BrowserAgent, BrowserApprovalRequired

router = APIRouter(prefix="/api/v1/browser", tags=["browser"])


class BrowserAction(BaseModel):
    type: str = Field(min_length=1)
    selector: str | None = None
    value: str | None = None
    url: str | None = None
    name: str | None = None
    allow_external: bool = False


class BrowserTestRequest(BaseModel):
    url: str = Field(min_length=1)
    actions: list[BrowserAction] = []
    allow_external: bool = False
    headless: bool = True


@router.get("/policy")
def policy() -> dict:
    return {"approved_domains": ["localhost", "127.0.0.1"], "external_domains_require_permission": True}


@router.post("/tests")
async def run_test(request: BrowserTestRequest, settings: Settings = Depends(get_settings)) -> dict:
    agent = BrowserAgent(f"{settings.projects_root}/.localforge/browser-evidence")
    try:
        result = await agent.run(request.url, [item.model_dump(exclude_none=True) for item in request.actions], request.allow_external, request.headless)
    except BrowserApprovalRequired as exc:
        raise HTTPException(status_code=428, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.__dict__ | {"evidence": result.evidence.__dict__}
