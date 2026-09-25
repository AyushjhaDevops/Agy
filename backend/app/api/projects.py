from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.services.context_engine import ContextEngine
from app.services.project_indexer import ProjectIndexer

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_indexer(settings: Settings = Depends(get_settings)) -> ProjectIndexer:
    return ProjectIndexer(settings.projects_root, settings.index_ignore, settings.max_file_size_bytes)


def project_or_404(indexer: ProjectIndexer, project_id: str):
    try:
        return indexer.resolve(project_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/tree")
def tree(project_id: str, indexer: ProjectIndexer = Depends(get_indexer)) -> dict:
    return indexer.tree(project_or_404(indexer, project_id))


@router.get("/{project_id}/summary")
def summary(project_id: str, indexer: ProjectIndexer = Depends(get_indexer)) -> dict:
    return indexer.summary(project_or_404(indexer, project_id))


@router.get("/{project_id}/files")
def files(project_id: str, indexer: ProjectIndexer = Depends(get_indexer)) -> dict:
    project = project_or_404(indexer, project_id)
    return {"files": [str(path.relative_to(project.root)) for path in indexer.files(project)]}


@router.get("/{project_id}/file")
def read_file(project_id: str, path: str = Query(...), indexer: ProjectIndexer = Depends(get_indexer)) -> dict:
    project = project_or_404(indexer, project_id)
    try:
        return {"path": path, "content": indexer.read(project, path)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc


@router.get("/{project_id}/search")
def search(project_id: str, q: str = Query(..., min_length=1), indexer: ProjectIndexer = Depends(get_indexer)) -> dict:
    return {"results": indexer.search(project_or_404(indexer, project_id), q)}


@router.get("/{project_id}/context")
def context(project_id: str, task: str = Query(..., min_length=1), indexer: ProjectIndexer = Depends(get_indexer)) -> dict:
    project = project_or_404(indexer, project_id)
    return {"files": ContextEngine(indexer).select(project, task)}
