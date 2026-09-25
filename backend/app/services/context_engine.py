from pathlib import Path

from app.services.project_indexer import Project, ProjectIndexer


class ContextEngine:
    KEYWORDS = {"auth": {"auth", "login", "user", "session", "token", "permission", "middleware"}, "authentication": {"auth", "login", "user", "session", "token", "permission", "middleware"}, "security": {"auth", "security", "permission", "token", "password"}}

    def __init__(self, indexer: ProjectIndexer) -> None:
        self.indexer = indexer

    def select(self, project: Project, task: str, limit: int = 20) -> list[dict]:
        terms = set(task.lower().split())
        terms |= {value for key, values in self.KEYWORDS.items() if key in task.lower() for value in values}
        selected = []
        for path in self.indexer.files(project):
            relative = str(path.relative_to(project.root)).lower()
            score = sum(2 if term in Path(relative).name else 1 for term in terms if term in relative)
            if "test" in relative or "spec" in relative:
                score += 1
            if score:
                selected.append((score, path))
        selected.sort(key=lambda item: (-item[0], str(item[1])))
        return [{"file": str(path.relative_to(project.root)), "score": score} for score, path in selected[:limit]]
