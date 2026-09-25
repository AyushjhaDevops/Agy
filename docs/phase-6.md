# Phase 6 complete: safe terminal execution

The backend provides an async `CommandExecutor` with stdout/stderr streaming, exit codes, timeout, cancellation, and project-root working-directory validation. The command policy classifies commands as LOW, MEDIUM, HIGH, or CRITICAL.

`restricted`, `developer`, and `trusted` are application-level policy modes only. They are not OS-level isolation. Use a container, VM, OS sandbox, or separate unprivileged account when actual isolation is required.

High and critical commands require explicit approval. The terminal endpoints are:

- `GET /api/v1/terminal/policies`
- `GET /api/v1/terminal/history`
- `POST /api/v1/terminal/execute`
- `POST /api/v1/terminal/{execution_id}/stop`

`frontend/src/TerminalPanel.tsx` contains the terminal UI component with policy selection, working directory, output, history, clear, and stop controls.
