import pytest

from app.services.git_service import GitOperationForbidden, GitService


def test_git_status_shows_branch_and_changes(tmp_path) -> None:
    """Test Git status reading."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("content")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    service = GitService(str(repo))
    status = service.status()
    assert status.branch == "master" or status.branch == "main"
    assert status.ahead == 0 and status.behind == 0


def test_commit_requires_approval(tmp_path) -> None:
    """Test that commit requires approval."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("content")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)
    service = GitService(str(repo))
    with pytest.raises(GitOperationForbidden):
        service.commit("test message", approved=False)


def test_reset_requires_approval(tmp_path) -> None:
    """Test that reset requires approval."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("content")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    service = GitService(str(repo))
    with pytest.raises(GitOperationForbidden):
        service.reset("HEAD", approved=False)
