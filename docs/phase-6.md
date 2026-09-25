# Phase 6: safe terminal execution

Phase 6 adds an asynchronous terminal service with command classification, approval gates, configurable execution policy, cancellation, timeouts, working-directory validation, and bounded command history.

## Important security boundary

The application policy is **not OS-level isolation**. `restricted`, `developer`, and `trusted` are application-level policies only. Use a real container, VM, OS sandbox, or separate unprivileged account when isolation is required.

High and critical commands always require explicit approval. The executor passes only a small environment allowlist and constrains working directories to the configured projects root.

## API

- `GET /api/v1/terminal/policies`
- `POST /api/v1/terminal/execute`
- `GET /api/v1/terminal/history`
- `POST /api/v1/terminal/{execution_id}/stop`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/terminal/execute \
  -H 'Content-Type: application/json' \
  -d '{"command":"pytest","policy":"developer","cwd":"current"}'
```

A high-risk command without approval returns HTTP `428`. A restricted-policy medium command returns HTTP `403`.
