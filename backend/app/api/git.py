from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.git_service import GitOperationForbidden, GitService

router = APIRouter(prefix="/api/v1/git", tags=["git"])


class CommitRequest(BaseModel):
    message: str = Field(min_length=1)
    approved: bool = False


class ResetRequest(BaseModel):
    ref: str = "HEAD"
    approved: bool = False


class RebaseRequest(BaseModel):
    branch: str = Field(min_length=1)
    approved: bool = False


class CheckoutRequest(BaseModel):
    branch: str = Field(min_length=1)


class AddRequest(BaseModel):
    files: list[str] | None = None


def git_service(settings: Settings = Depends(get_settings)) -> GitService:
    return GitService(settings.projects_root)


@router.get("/status")
def status(service: GitService = Depends(git_service)) -> dict:
    s = service.status()
    return {"branch": s.branch, "ahead": s.ahead, "behind": s.behind, "modified": s.modified, "added": s.added, "deleted": s.deleted, "untracked": s.untracked}


@router.get("/diff")
def diff(file: str | None = None, service: GitService = Depends(git_service)) -> dict:
    diffs = service.diff(file)
    return {"diffs": [{"file": d.file, "insertions": d.insertions, "deletions": d.deletions, "patch": d.patch} for d in diffs]}


@router.get("/log")
def log(n: int = 20, service: GitService = Depends(git_service)) -> dict:
    commits = service.log(n)
    return {"commits": [{"hash": c.hash, "author": c.author, "timestamp": c.timestamp, "message": c.message} for c in commits]}


@router.get("/branches")
def branches(service: GitService = Depends(git_service)) -> dict:
    return service.branches()


@router.post("/checkout")
def checkout(request: CheckoutRequest, service: GitService = Depends(git_service)) -> dict:
    try:
        service.checkout(request.branch)
        return {"status": "checked out", "branch": request.branch}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/add")
def add(request: AddRequest, service: GitService = Depends(git_service)) -> dict:
    try:
        service.add(request.files)
        return {"status": "staged", "files": request.files or "all"}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/commit")
def commit(request: CommitRequest, service: GitService = Depends(git_service)) -> dict:
    if not request.approved:
        raise HTTPException(status_code=428, detail="Commit requires explicit approval")
    try:
        service.commit(request.message, approved=True)
        return {"status": "committed", "message": request.message}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stash")
def stash(service: GitService = Depends(git_service)) -> dict:
    try:
        result = service.stash()
        return {"status": "stashed", "result": result}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/show/{ref}")
def show(ref: str = "HEAD", service: GitService = Depends(git_service)) -> dict:
    try:
        content = service.show(ref)
        return {"ref": ref, "content": content}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/blame/{file_path}")
def blame(file_path: str, service: GitService = Depends(git_service)) -> dict:
    try:
        result = service.blame(file_path)
        return {"file": file_path, "blame": result}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset")
def reset(request: ResetRequest, service: GitService = Depends(git_service)) -> dict:
    if not request.approved:
        raise HTTPException(status_code=428, detail="Reset requires explicit approval")
    try:
        service.reset(request.ref, approved=True)
        return {"status": "reset", "ref": request.ref}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rebase")
def rebase(request: RebaseRequest, service: GitService = Depends(git_service)) -> dict:
    if not request.approved:
        raise HTTPException(status_code=428, detail="Rebase requires explicit approval")
    try:
        service.rebase(request.branch, approved=True)
        return {"status": "rebased", "branch": request.branch}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
