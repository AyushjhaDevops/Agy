from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_IGNORES = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "coverage"}
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf", ".zip", ".tar", ".gz", ".db", ".sqlite", ".woff", ".woff2", ".mp3", ".mp4", ".mov", ".exe", ".bin"}
LANGUAGE_EXTENSIONS = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".rb": "Ruby", ".php": "PHP", ".c": "C", ".cpp": "C++", ".h": "C/C++", ".cs": "C#", ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON", ".md": "Markdown"}


@dataclass(frozen=True)
class Project:
    project_id: str
    root: Path


class ProjectIndexer:
    def __init__(self, projects_root: str, ignores: str = "", max_file_size: int = 1_000_000) -> None:
        self.projects_root = Path(projects_root).expanduser().resolve()
        self.ignores = DEFAULT_IGNORES | {item.strip() for item in ignores.split(",") if item.strip()}
        self.max_file_size = max_file_size

    def resolve(self, project_id: str) -> Project:
        if project_id in {".", "root", "current"}:
            root = self.projects_root
        else:
            candidate = (self.projects_root / project_id).resolve()
            if self.projects_root not in candidate.parents and candidate != self.projects_root:
                raise ValueError("Project path escapes the configured projects root")
            root = candidate
        if not root.is_dir():
            raise FileNotFoundError(f"Project does not exist: {project_id}")
        return Project(project_id, root)

    def _ignored(self, path: Path, root: Path) -> bool:
        return any(part in self.ignores for part in path.relative_to(root).parts)

    def files(self, project: Project) -> list[Path]:
        return sorted((path for path in project.root.rglob("*") if path.is_file() and not self._ignored(path, project.root) and path.stat().st_size <= self.max_file_size), key=lambda p: str(p))

    def tree(self, project: Project) -> dict:
        root = {"name": project.root.name, "path": "", "kind": "directory", "children": []}
        nodes = {"": root}
        for path in self.files(project):
            relative = path.relative_to(project.root)
            parent = ""
            for part in relative.parts[:-1]:
                current = f"{parent}/{part}".strip("/")
                if current not in nodes:
                    node = {"name": part, "path": current, "kind": "directory", "children": []}
                    nodes[parent]["children"].append(node)
                    nodes[current] = node
                parent = current
            file_path = str(relative)
            nodes[parent]["children"].append({"name": relative.name, "path": file_path, "kind": "file", "language": LANGUAGE_EXTENSIONS.get(path.suffix.lower())})
        self._sort_tree(root)
        return root

    def _sort_tree(self, node: dict) -> None:
        node["children"].sort(key=lambda item: (item["kind"] != "directory", item["name"].lower()))
        for child in node["children"]:
            self._sort_tree(child)

    def summary(self, project: Project) -> dict:
        files = self.files(project)
        languages: dict[str, int] = {}
        for path in files:
            language = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
            if language:
                languages[language] = languages.get(language, 0) + 1
        names = {path.name.lower() for path in files}
        package_managers = [name for name in ("npm", "pnpm", "yarn", "pip", "poetry", "cargo", "go") if any(token in names for token in {f"{name}.json", "package.json"} if name == "npm" or token in names)]
        frameworks = []
        package = next((path for path in files if path.name == "package.json"), None)
        if package:
            try:
                data = json.loads(package.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                frameworks = [name for name in ("react", "next", "vue", "angular", "fastapi", "django", "express") if name in deps]
            except (OSError, json.JSONDecodeError):
                pass
        git = None
        try:
            git = subprocess.run(["git", "-C", str(project.root), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=3, check=False).stdout.strip() or None
        except (OSError, subprocess.TimeoutExpired):
            pass
        tests = [str(path.relative_to(project.root)) for path in files if "test" in path.name.lower() or "spec" in path.name.lower()]
        configs = [str(path.relative_to(project.root)) for path in files if path.name.lower() in {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "pyproject.toml", "package.json", "vite.config.ts", "vite.config.js", "makefile"} or path.name.startswith(".github")]
        readmes = [str(path.relative_to(project.root)) for path in files if path.name.lower().startswith("readme")]
        return {"project_id": project.project_id, "root": str(project.root), "file_count": len(files), "languages": languages, "package_managers": package_managers, "frameworks": frameworks, "git_branch": git, "test_files": tests[:100], "configuration_files": configs[:100], "readme_files": readmes, "entry_points": [item for item in ("src/main.tsx", "src/main.py", "main.py", "app/main.py", "index.html") if (project.root / item).exists()]}

    def read(self, project: Project, relative_path: str) -> str:
        candidate = (project.root / relative_path).resolve()
        if project.root not in candidate.parents or not candidate.is_file():
            raise FileNotFoundError("File is outside the project or does not exist")
        if candidate.stat().st_size > self.max_file_size or candidate.suffix.lower() in BINARY_EXTENSIONS:
            raise ValueError("Binary or oversized files cannot be read")
        try:
            return candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Binary files cannot be read") from exc

    def search(self, project: Project, query: str) -> list[dict]:
        if not query.strip():
            return []
        rg = subprocess.run(["rg", "--line-number", "--column", "--no-heading", "--color", "never", "--fixed-strings", query, str(project.root)], capture_output=True, text=True, timeout=10, check=False) if __import__("shutil").which("rg") else None
        if rg is not None and rg.returncode in (0, 1):
            results = []
            for line in rg.stdout.splitlines()[:200]:
                parts = line.split(":", 3)
                if len(parts) == 4:
                    file, number, column, snippet = parts
                    results.append({"file": str(Path(file).relative_to(project.root)), "line": int(number), "column": int(column), "snippet": snippet[:500]})
            return results
        results = []
        for path in self.files(project):
            try:
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    column = line.find(query)
                    if column >= 0:
                        results.append({"file": str(path.relative_to(project.root)), "line": number, "column": column + 1, "snippet": line[:500]})
            except UnicodeDecodeError:
                continue
        return results[:200]
