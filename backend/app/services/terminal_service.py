from __future__ import annotations

import asyncio
import os
import shlex
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import AsyncIterator


class CommandRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionPolicy(StrEnum):
    RESTRICTED = "restricted"
    DEVELOPER = "developer"
    TRUSTED = "trusted"


@dataclass(frozen=True)
class CommandDecision:
    risk: CommandRisk
    requires_approval: bool
    allowed: bool
    reason: str


@dataclass
class CommandResult:
    command: str
    cwd: str
    risk: CommandRisk
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False
    duration: float = 0.0


class CommandApprovalRequired(PermissionError):
    pass


class CommandPolicy:
    _critical = {"sudo", "su", "doas", "mkfs", "fdisk", "parted", "cryptsetup", "pass", "gpg", "ssh-add"}
    _high = {"rm", "rmdir", "unlink", "chmod", "chown", "chgrp", "git reset", "git clean", "git push --force", "dd"}
    _medium = {"npm install", "npm i", "pip install", "pip3 install", "poetry install", "docker build", "docker compose build"}

    def __init__(self, policy: ExecutionPolicy = ExecutionPolicy.RESTRICTED) -> None:
        self.policy = policy

    def classify(self, command: str) -> CommandRisk:
        normalized = " ".join(command.lower().split())
        try:
            tokens = shlex.split(normalized)
        except ValueError:
            return CommandRisk.CRITICAL
        if any(token in self._critical for token in tokens) or any(normalized.startswith(item) for item in self._critical):
            return CommandRisk.CRITICAL
        if any(normalized == item or normalized.startswith(item + " ") for item in self._high):
            return CommandRisk.HIGH
        if any(normalized == item or normalized.startswith(item + " ") for item in self._medium):
            return CommandRisk.MEDIUM
        if any(operator in normalized for operator in (";", "&&", "||", "|", ">", "<", "`", "$(`)):
            return CommandRisk.MEDIUM
        return CommandRisk.LOW

    def decide(self, command: str, approved: bool = False) -> CommandDecision:
        risk = self.classify(command)
        if risk in {CommandRisk.HIGH, CommandRisk.CRITICAL} and not approved:
            return CommandDecision(risk, True, False, "Explicit approval is required for high-risk commands")
        if self.policy == ExecutionPolicy.RESTRICTED and risk != CommandRisk.LOW:
            return CommandDecision(risk, False, False, "Restricted policy permits low-risk commands only")
        return CommandDecision(risk, risk in {CommandRisk.HIGH, CommandRisk.CRITICAL}, True, "Allowed by execution policy")


class CommandExecutor:
    """Async command runner; this is a policy gate, not OS-level sandboxing."""

    def __init__(self, root: str, policy: ExecutionPolicy = ExecutionPolicy.RESTRICTED, timeout: float = 120.0) -> None:
        self.root = Path(root).expanduser().resolve()
        self.policy = CommandPolicy(policy)
        self.timeout = timeout
        self.processes: dict[str, asyncio.subprocess.Process] = {}

    def _cwd(self, cwd: str | None) -> Path:
        path = (self.root / cwd).resolve() if cwd else self.root
        if path != self.root and self.root not in path.parents:
            raise ValueError("Working directory must remain inside the configured project root")
        if not path.is_dir():
            raise FileNotFoundError(f"Working directory does not exist: {path}")
        return path

    @staticmethod
    def _environment() -> dict[str, str]:
        # Do not pass the complete parent environment to commands.
        allowed = {"PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR"}
        return {key: value for key, value in os.environ.items() if key in allowed}

    async def stream(self, command: str, cwd: str | None = None, approved: bool = False, timeout: float | None = None, execution_id: str | None = None) -> AsyncIterator[tuple[str, str]]:
        decision = self.policy.decide(command, approved)
        if not decision.allowed:
            if decision.requires_approval:
                raise CommandApprovalRequired(decision.reason)
            raise PermissionError(decision.reason)
        process = await asyncio.create_subprocess_shell(command, cwd=str(self._cwd(cwd)), env=self._environment(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        if execution_id:
            self.processes[execution_id] = process
        async def read(stream: asyncio.StreamReader | None, channel: str) -> AsyncIterator[tuple[str, str]]:
            if stream:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    yield channel, line.decode(errors="replace")
        try:
            async def collect() -> None:
                async with asyncio.TaskGroup() as group:
                    group.create_task(self._forward(read(process.stdout, "stdout")))
                    group.create_task(self._forward(read(process.stderr, "stderr")))
            # The public stream needs to yield live events, so consume both pipes fairly.
            stdout_task = asyncio.create_task(process.stdout.readline()) if process.stdout else None
            stderr_task = asyncio.create_task(process.stderr.readline()) if process.stderr else None
            while stdout_task or stderr_task:
                pending = [task for task in (stdout_task, stderr_task) if task]
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    line = task.result()
                    channel = "stdout" if task is stdout_task else "stderr"
                    if line:
                        yield channel, line.decode(errors="replace")
                        replacement = asyncio.create_task((process.stdout if channel == "stdout" else process.stderr).readline())
                        if channel == "stdout": stdout_task = replacement
                        else: stderr_task = replacement
                    elif channel == "stdout": stdout_task = None
                    else: stderr_task = None
            await asyncio.wait_for(process.wait(), timeout=timeout or self.timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
        finally:
            self.processes.pop(execution_id or "", None)

    async def execute(self, command: str, cwd: str | None = None, approved: bool = False, timeout: float | None = None, execution_id: str | None = None) -> CommandResult:
        decision = self.policy.decide(command, approved)
        if not decision.allowed:
            if decision.requires_approval: raise CommandApprovalRequired(decision.reason)
            raise PermissionError(decision.reason)
        started = time.perf_counter(); out: list[str] = []; err: list[str] = []
        try:
            async for channel, text in self.stream(command, cwd, approved, timeout, execution_id):
                (out if channel == "stdout" else err).append(text)
            process_code = 0
            if execution_id and execution_id in self.processes: process_code = await self.processes[execution_id].wait()
            return CommandResult(command, str(self._cwd(cwd)), decision.risk, process_code, "".join(out), "".join(err), duration=time.perf_counter() - started)
        except asyncio.TimeoutError:
            return CommandResult(command, str(self._cwd(cwd)), decision.risk, None, "".join(out), "".join(err), timed_out=True, duration=time.perf_counter() - started)
        except asyncio.CancelledError:
            await self.cancel(execution_id) if execution_id else None
            raise

    async def cancel(self, execution_id: str | None) -> bool:
        process = self.processes.get(execution_id or "")
        if not process or process.returncode is not None: return False
        process.kill()
        await process.wait()
        return True

    async def _forward(self, stream: AsyncIterator[tuple[str, str]]) -> None:
        async for _ in stream: pass
