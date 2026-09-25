from pathlib import Path

import pytest
from app.services.project_indexer import ProjectIndexer


@pytest.fixture
def project(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
    (tmp_path / "src" / "auth_test.py").write_text("from auth import login\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("ignore", encoding="utf-8")
    return ProjectIndexer(str(tmp_path)), tmp_path


def test_tree_ignores_directories(project):
    indexer, _ = project
    tree = indexer.tree(indexer.resolve("current"))
    paths = str(tree)
    assert "auth.py" in paths
    assert "ignored.js" not in paths


def test_read_and_search(project):
    indexer, _ = project
    resolved = indexer.resolve("current")
    assert "login" in indexer.read(resolved, "src/auth.py")
    assert indexer.search(resolved, "login")[0]["line"] == 1


def test_context_selects_auth_files(project):
    indexer, _ = project
    selected = indexer and __import__("app.services.context_engine", fromlist=["ContextEngine"]).ContextEngine(indexer).select(indexer.resolve("current"), "Fix authentication")
    assert any(item["file"] == "src/auth.py" for item in selected)
