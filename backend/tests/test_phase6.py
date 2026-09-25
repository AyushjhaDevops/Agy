from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.services.terminal_service import CommandApprovalRequired, CommandExecutor, CommandRisk, ExecutionPolicy


@pytest.mark.anyio
async def test_success_failure_and_working_directory(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.DEVELOPER)
    result = await runner.execute("pwd")
    assert result.returncode == 0 and str(tmp_path) in result.stdout
    result = await runner.execute("python -c 'import sys; print(\"bad\", file=sys.stderr); sys.exit(3)'")
    assert result.returncode == 3 and "bad" in result.stderr


@pytest.mark.anyio
async def test_timeout_and_cancellation(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.DEVELOPER)
    result = await runner.execute("python -c 'import time; time.sleep(1)'", timeout=0.01)
    assert result.timed_out
    task = asyncio.create_task(runner.execute("python -c 'import time; time.sleep(5)'", execution_id="stop-me"))
    await asyncio.sleep(0.05)
    assert await runner.cancel("stop-me")
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.anyio
async def test_approval_and_streaming(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.DEVELOPER)
    assert runner.policy.classify("rm -rf x") == CommandRisk.HIGH
    with pytest.raises(CommandApprovalRequired):
        await runner.execute("rm -rf x")
    events = [event async for event in runner.stream("python -c 'print(\"hello\")'")]
    assert any(channel == "stdout" and "hello" in text for channel, text in events)


def test_restricted_policy_rejects_medium(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.RESTRICTED)
    assert not runner.policy.decide("npm install").allowed
