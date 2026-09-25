# Phase 5: specialized agents

Phase 5 adds a dependency-aware multi-agent orchestration layer.

## Agents

Planner, Coder, Reviewer, Debugger, Tester, Security, Git, Browser, and Researcher agents have isolated memory instructions and task context.

## API

- `GET /api/v1/agents` lists available agents.
- `POST /api/v1/agents/runs` validates a task graph and executes ready independent tasks concurrently.
- `GET /api/v1/agents/runs/{run_id}` returns statuses, actions, durations, and results.
- `POST /api/v1/agents/runs/{run_id}/cancel` requests cancellation.

Example graph:

```json
{
  "goal": "Review a feature",
  "tasks": [
    {"name": "plan", "agent": "planner", "goal": "plan"},
    {"name": "code", "agent": "coder", "goal": "code", "dependencies": ["plan"]},
    {"name": "security", "agent": "security", "goal": "scan", "dependencies": ["plan"]},
    {"name": "review", "agent": "reviewer", "goal": "review", "dependencies": ["code", "security"]}
  ]
}
```

Execution is bounded by dependency completion and retry count. File editing and dangerous tools remain approval-gated from Phase 4.
