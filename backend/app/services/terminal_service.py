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
    """Raised when a high-risk command has not been explicitly approved."""


class CommandPolicy:
    _critical_commands = {"sudo", "su", "doas", "mkfs", "fdisk", "parted", "cryptsetup", "gpg", "ssh-add"}
    _high_prefixes = ("rm", "rmdir", "unlink", "chmod", "chown", "chgrp", "git reset", "git clean", "git push --force", "dd")
    _medium_prefixes = ("npm install", "npm i", "pip install", "pip3 install", "poetry install", "docker build", "docker compose build")

    def __init__(self, policy: ExecutionPolicy = ExecutionPolicy.RESTRICTED) -> None:
        self.policy = policy

    def classify(self, command: str) -> CommandRisk:
        normalized = " ".join(command.lower().split())
        try:
            tokens = shlex.split(normalized)
        except ValueError:
            return CommandRisk.CRITICAL
        if tokens and (
            tokens[0] in self._critical_commands
            or any(normalized == item or normalized.startswith(item + " ") for item in self._critical_commands)
        ):
            return CommandRisk.CRITICAL
        if any(normalized == item or normalized.startswith(item + " ") for item in self._high_prefixes):
            return CommandRisk.HIGH
        if any(normalized == item or normalized.startswith(item + " ") for item in self._medium_prefixes):
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
        return CommandDecision(risk, False, True, "Allowed by execution policy")


class CommandExecutor:
    """Async process runner and policy gate; this is not OS-level sandboxing."""

    def __init__(self, root: str, policy: ExecutionPolicy = ExecutionPolicy.RESTRICTED, timeout: float = 120.0) -> None:
        self.root = Path(root).expanduser().resolve()
        self.policy = CommandPolicy(policy)
        self.timeout = timeout
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.returncodes: dict[str, int | None] = {}

    def _cwd(self, cwd: str | None) -> Path:
        path = (self.root / cwd).resolve() if cwd else self.root
        if path != self.root and self.root not in path.parents:
            raise ValueError("Working directory must remain inside the configured project root")
        if not path.is_dir():
            raise FileNotFoundError(f"Working directory does not exist: {path}")
        return path

    @staticmethod
    def _environment() -> dict[str, str]:
        allowed = {"PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR"}
        return {key: value for key, value in os.environ.items() if key in allowed}

    def _check(self, command: str, approved: bool) -> CommandDecision:
        decision = self.policy.decide(command, approved)
        if not decision.allowed:
            if decision.requires_approval:
                raise CommandApprovalRequired(decision.reason)
            raise PermissionError(decision.reason)
        return decision

    async def stream(self, command: str, cwd: str | None = None, approved: bool = False, timeout: float | None = None, execution_id: str | None = None) -> AsyncIterator[tuple[str, str]]:
        self._check(command, approved)
        process = await asyncio.create_subprocess_shell(command, cwd=str(self._cwd(cwd)), env=self._environment(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        if execution_id:
            self.processes[execution_id] = process
        tasks: dict[asyncio.Task[bytes], str] = {}
        if process.stdout:
            tasks[asyncio.create_task(process.stdout.readline())] = "stdout"
        if process.stderr:
            tasks[asyncio.create_task(process.stderr.readline())] = "stderr"
        deadline = asyncio.get_running_loop().time() + (timeout or self.timeout)
        try:
            while tasks:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise asyncio.TimeoutError
                done, _ = await asyncio.wait(tasks, timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
                if not done:
                    raise asyncio.TimeoutError
                for task in done:
                    channel = tasks.pop(task)
                    line = task.result()
                    if line:
                        yield channel, line.decode(errors="replace")
                        stream = process.stdout if channel == "stdout" else process.stderr
                        if stream:
                            tasks[asyncio.create_task(stream.readline())] = channel
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            await asyncio.wait_for(process.wait(), remaining)
            if execution_id:
                self.returncodes[execution_id] = process.returncode
        except (asyncio.TimeoutError, asyncio.CancelledError):
            await self._kill(process)
            if execution_id:
                self.returncodes[execution_id] = process.returncode
            raise
        finally:
            for task in tasks:
                task.cancel()
            if execution_id and self.processes.get(execution_id) is process:
                self.processes.pop(execution_id, None)

    async def execute(self, command: str, cwd: str | None = None, approved: bool = False, timeout: float | None = None, execution_id: str | None = None) -> CommandResult:
        decision = self._check(command, approved)
        started = time.perf_counter()
        stdout: list[str] = []
        stderr: list[str] = []
        try:
            async for channel, text in self.stream(command, cwd, approved, timeout, execution_id):
                (stdout if channel == "stdout" else stderr).append(text)
            return CommandResult(command, str(self._cwd(cwd)), decision.risk, self.returncodes.pop(execution_id, 0) if execution_id else 0, "".join(stdout), "".join(stderr), duration=time.perf_counter() - started)
        except asyncio.TimeoutError:
            return CommandResult(command, str(self._cwd(cwd)), decision.risk, self.returncodes.pop(execution_id, None) if execution_id else None, "".join(stdout), "".join(stderr), timed_out=True, duration=time.perf_counter() - started)
        except asyncio.CancelledError:
            await self.cancel(execution_id)
            raise

    async def cancel(self, execution_id: str | None) -> bool:
        process = self.processes.get(execution_id or "")
        if not process or process.returncode is not None:
            return False
        await self._kill(process)
        return True

    @staticmethod
    async def _kill(process: asyncio.subprocess.Process) -> None:
        if process.returncode is None:
            process.kill()
        await process.wait()
