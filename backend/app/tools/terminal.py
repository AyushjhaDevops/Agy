from __future__ import annotations

import subprocess
from typing import Any

from app.tools.base import ToolSpec


class TerminalTool:
    spec = ToolSpec("terminal", "Run a non-destructive project command", {"command": {"type": "string"}}, {"returncode": {"type": "integer"}, "stdout": {"type": "string"}, "stderr": {"type": "string"}}, "HIGH")
    name, description, input_schema, output_schema, risk_level = spec.name, spec.description, spec.input_schema, spec.output_schema, spec.risk_level
    _blocked = ("rm -rf", "sudo ", "git push --force", "git reset --hard", "mkfs", "dd if=", "chmod 777")

    def __init__(self, cwd: str) -> None:
        self.cwd = cwd

    def execute(self, **inputs: Any) -> dict[str, Any]:
        command = inputs["command"]
        if any(item in command.lower() for item in self._blocked) and not inputs.get("approved", False):
            raise PermissionError("Dangerous command requires explicit approval")
        result = subprocess.run(command, cwd=self.cwd, shell=True, capture_output=True, text=True, timeout=120, check=False)
        return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


class TestTool(TerminalTool):
    spec = ToolSpec("test", "Run the configured test command", {"command": {"type": "string"}}, {"returncode": {"type": "integer"}, "stdout": {"type": "string"}, "stderr": {"type": "string"}}, "MEDIUM")
    name, description, input_schema, output_schema, risk_level = spec.name, spec.description, spec.input_schema, spec.output_schema, spec.risk_level


class GitDiffTool(TerminalTool):
    spec = ToolSpec("git.diff", "Inspect uncommitted changes", {}, {"stdout": {"type": "string"}}, "LOW")
    name, description, input_schema, output_schema, risk_level = spec.name, spec.description, spec.input_schema, spec.output_schema, spec.risk_level

    def execute(self, **inputs: Any) -> dict[str, Any]:
        return super().execute(command="git diff --no-ext-diff", **inputs)
