# Phase 3: repository understanding

Phase 3 adds a safe, read-only repository index and context layer.

## API

With `LOCALFORGE_PROJECTS_ROOT` unset, `current` points to the configured working directory. For multiple projects, set the root and use a child directory as `project_id`.

- `GET /api/v1/projects/{project_id}/tree`
- `GET /api/v1/projects/{project_id}/summary`
- `GET /api/v1/projects/{project_id}/file?path=...`
- `GET /api/v1/projects/{project_id}/search?q=...`
- `GET /api/v1/projects/{project_id}/context?task=...`

The reader rejects binary and oversized files. Search uses `rg` when available and a bounded Python fallback otherwise. Project paths are constrained beneath `PROJECTS_ROOT`.

Autonomous modification and command execution remain intentionally out of scope.
