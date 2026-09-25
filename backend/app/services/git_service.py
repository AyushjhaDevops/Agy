from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class GitOperationForbidden(PermissionError):
    pass


@dataclass
class GitStatus:
    branch: str
    ahead: int
    behind: int
    modified: list[str]
    added: list[str]
    deleted: list[str]
    untracked: list[str]


@dataclass
class GitDiff:
    file: str
    insertions: int
    deletions: int
    patch: str


@dataclass
class GitCommit:
    hash: str
    author: str
    timestamp: str
    message: str


class GitService:
    """Git wrapper with approval gates for dangerous operations."""

    def __init__(self, repo_path: str) -> None:
        self.repo = Path(repo_path).expanduser().resolve()
        if not (self.repo / ".git").is_dir():
            raise ValueError(f"{repo_path} is not a Git repository")

    def _run(self, *args: str, check: bool = True) -> str:
        try:
            result = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=check)
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Git command failed: {exc.stderr}") from exc

    def status(self) -> GitStatus:
        branch = self._run("rev-parse", "--abbrev-ref", "HEAD")
        try:
            ahead_behind = self._run("rev-list", "--left-right", "--count", "@{u}...HEAD").split()
            behind, ahead = int(ahead_behind[0]), int(ahead_behind[1])
        except (IndexError, ValueError):
            ahead = behind = 0
        porcelain = self._run("status", "--porcelain")
        modified = [line[3:] for line in porcelain.split("\n") if line.startswith(" M")]
        added = [line[3:] for line in porcelain.split("\n") if line.startswith("A ")]
        deleted = [line[3:] for line in porcelain.split("\n") if line.startswith(" D")]
        untracked = [line[3:] for line in porcelain.split("\n") if line.startswith("??")]
        return GitStatus(branch, ahead, behind, modified, added, deleted, untracked)

    def diff(self, file: str | None = None) -> list[GitDiff]:
        if file:
            patch = self._run("diff", "HEAD", file)
            insertions = patch.count("\n+") - 1
            deletions = patch.count("\n-") - 1
            return [GitDiff(file, insertions, deletions, patch)]
        diffs = []
        for diff_stat in self._run("diff", "--stat").split("\n"):
            if not diff_stat.strip() or "|" not in diff_stat:
                continue
            parts = diff_stat.split("|")
            file_name = parts[0].strip()
            changes = parts[1].split()
            insertions = sum(1 for _ in changes if _ == "+")
            deletions = sum(1 for _ in changes if _ == "-")
            patch = self._run("diff", "HEAD", file_name)
            diffs.append(GitDiff(file_name, insertions, deletions, patch))
        return diffs

    def log(self, n: int = 20) -> list[GitCommit]:
        commits = []
        log_output = self._run("log", f"--max-count={n}", "--format=%H%n%an%n%aI%n%B%n---")
        for chunk in log_output.split("---"):
            if not chunk.strip():
                continue
            lines = chunk.strip().split("\n")
            if len(lines) >= 3:
                commits.append(GitCommit(lines[0], lines[1], lines[2], "\n".join(lines[3:])))
        return commits

    def branches(self) -> dict[str, Any]:
        local = self._run("branch", "-v").split("\n")
        remote = self._run("branch", "-r", "-v").split("\n")
        return {"local": [b.strip() for b in local if b.strip()], "remote": [b.strip() for b in remote if b.strip()]}

    def checkout(self, branch: str) -> None:
        self._run("checkout", branch)

    def add(self, files: list[str] | None = None) -> None:
        if files:
            self._run("add", *files)
        else:
            self._run("add", "-A")

    def commit(self, message: str, approved: bool = False) -> str:
        if not approved:
            raise GitOperationForbidden("Commit requires explicit approval")
        return self._run("commit", "-m", message)

    def stash(self) -> str:
        return self._run("stash", "push")

    def show(self, ref: str = "HEAD") -> str:
        return self._run("show", ref)

    def blame(self, file: str) -> str:
        return self._run("blame", file)

    def reset(self, ref: str = "HEAD", approved: bool = False) -> None:
        if not approved:
            raise GitOperationForbidden("Reset requires explicit approval")
        self._run("reset", ref)

    def rebase(self, branch: str, approved: bool = False) -> None:
        if not approved:
            raise GitOperationForbidden("Rebase requires explicit approval")
        self._run("rebase", branch)
