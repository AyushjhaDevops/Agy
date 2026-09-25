from __future__ import annotations

import difflib
import shutil
from pathlib import Path
from typing import Any

from app.services.project_indexer import BINARY_EXTENSIONS, Project
from app.tools.base import ToolSpec

_SENSITIVE = {".env", "id_rsa", "credentials", "credentials.json", "secret", "secrets"}


def safe_path(project: Project, relative: str) -> Path:
    candidate = (project.root / relative).resolve()
    if project.root not in candidate.parents or not candidate.is_file():
        raise ValueError("Path is outside the project or does not exist")
    if candidate.name in _SENSITIVE or any(part in _SENSITIVE for part in candidate.parts):
        raise PermissionError("Sensitive files are not available to agents")
    return candidate


class FileReadTool:
    spec = ToolSpec("file.read", "Read a safe text file", {"path": {"type": "string"}}, {"content": {"type": "string"}}, "LOW")
    name, description, input_schema, output_schema, risk_level = spec.name, spec.description, spec.input_schema, spec.output_schema, spec.risk_level

    def __init__(self, project: Project, max_size: int = 1_000_000) -> None:
        self.project, self.max_size = project, max_size

    def execute(self, **inputs: Any) -> dict[str, Any]:
        path = safe_path(self.project, inputs["path"])
        if path.suffix.lower() in BINARY_EXTENSIONS or path.stat().st_size > self.max_size:
            raise ValueError("Binary or oversized files cannot be read")
        return {"path": inputs["path"], "content": path.read_text(encoding="utf-8")}


class FileSearchTool:
    spec = ToolSpec("file.search", "Search indexed project files", {"query": {"type": "string"}}, {"results": {"type": "array"}}, "LOW")
    name, description, input_schema, output_schema, risk_level = spec.name, spec.description, spec.input_schema, spec.output_schema, spec.risk_level

    def __init__(self, indexer: Any, project: Project) -> None:
        self.indexer, self.project = indexer, project

    def execute(self, **inputs: Any) -> dict[str, Any]:
        return {"results": self.indexer.search(self.project, inputs["query"]) }


class PatchTool:
    spec = ToolSpec("patch", "Generate and apply a focused unified diff", {"path": {"type": "string"}, "new_content": {"type": "string"}, "approved": {"type": "boolean"}}, {"diff": {"type": "string"}, "applied": {"type": "boolean"}}, "MEDIUM")
    name, description, input_schema, output_schema, risk_level = spec.name, spec.description, spec.input_schema, spec.output_schema, spec.risk_level

    def __init__(self, project: Project) -> None:
        self.project = project
        self.backups: dict[str, Path] = {}

    def execute(self, **inputs: Any) -> dict[str, Any]:
        relative, new_content = inputs["path"], inputs["new_content"]
        path = (self.project.root / relative).resolve()
        if self.project.root not in path.parents:
            raise ValueError("Patch path is outside the project")
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        diff = "".join(difflib.unified_diff(old.splitlines(True), new_content.splitlines(True), fromfile=relative, tofile=relative))
        if not inputs.get("approved", False):
            return {"diff": diff, "applied": False}
        if path.exists():
            backup = path.with_name(f".{path.name}.localforge.bak")
            shutil.copy2(path, backup)
            self.backups[relative] = backup
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding="utf-8")
        return {"diff": diff, "applied": True}

    def rollback(self, relative: str) -> None:
        backup = self.backups.get(relative)
        if backup and backup.exists():
            shutil.copy2(backup, self.project.root / relative)
            backup.unlink()
