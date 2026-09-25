# Phase 4: first coding-agent foundation

Phase 4 adds a bounded, approval-gated coding-agent foundation.

- Agent classes: `BaseAgent`, `CodingAgent`, `PlannerAgent`, `TestAgent`, and `DebuggerAgent`.
- Tool metadata and implementations for file reading/search, patching, terminal, tests, and Git diff.
- Diff-first patch workflow with backups and rollback support.
- Task state and plan API under `/api/v1/tasks`.
- Frontend task panel showing plans and task status.

The default task endpoint creates a plan only. File changes require a separate proposal and explicit approval. Dangerous terminal commands are blocked unless approved, and sensitive files such as `.env`, SSH keys, and credential files are not exposed through the agent file reader.

## API examples

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Create a users endpoint","project_id":"current"}'
```

The implementation intentionally stops before autonomous multi-step editing. Later phases can add durable task storage, approval policies, test execution orchestration, and richer patch validation.
