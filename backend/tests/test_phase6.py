import asyncio
from pathlib import Path

import pytest

from app.services.terminal_service import CommandApprovalRequired, CommandExecutor, CommandRisk, ExecutionPolicy


@pytest.mark.anyio
async def test_success_failure_and_working_directory(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.DEVELOPER)
    success = await runner.execute("pwd")
    assert success.returncode == 0 and str(tmp_path) in success.stdout
    failure = await runner.execute("python -c 'import sys; print(\"bad\", file=sys.stderr); sys.exit(3)'")
    assert failure.returncode == 3 and "bad" in failure.stderr


@pytest.mark.anyio
async def test_timeout_and_cancellation(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.DEVELOPER)
    timed = await runner.execute("python -c 'import time; time.sleep(1)'", timeout=0.01)
    assert timed.timed_out
    task = asyncio.create_task(runner.execute("python -c 'import time; time.sleep(5)'", execution_id="stop-me"))
    await asyncio.sleep(0.05)
    assert await runner.cancel("stop-me")
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task


@pytest.mark.anyio
async def test_approval_policy_and_streaming(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.DEVELOPER)
    assert runner.policy.classify("rm -rf x") == CommandRisk.HIGH
    with pytest.raises(CommandApprovalRequired): await runner.execute("rm -rf x")
    events = [event async for event in runner.stream("python -c 'print(\"hello\")'")]
    assert any(channel == "stdout" and "hello" in text for channel, text in events)


def test_restricted_policy_rejects_medium(tmp_path: Path) -> None:
    runner = CommandExecutor(str(tmp_path), ExecutionPolicy.RESTRICTED)
    with pytest.raises(PermissionError): runner.policy.decide("npm install")
