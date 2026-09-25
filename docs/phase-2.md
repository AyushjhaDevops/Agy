# Phase 2

Phase 2 adds the local Ollama model boundary and a real streamed chat experience.

## Included

- `ModelProvider` protocol with a concrete `OllamaProvider`.
- Ollama model discovery, health checks, generation, streaming, timeout and connection error mapping.
- `POST /api/v1/chat` and WebSocket `/api/v1/chat/stream`.
- SQLite conversation and message persistence.
- Frontend streamed chat, Markdown/code rendering, copy, stop, model selector, and connection status.
- Mocked backend tests that do not require Ollama.

## Run

Set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `.env`, install backend requirements, and install frontend dependencies:

```bash
cd backend && source .venv/bin/activate && pip install -r requirements.txt
cd ../frontend && npm install
```

Start Ollama, then the API and frontend as in the root README. An empty `OLLAMA_MODEL` is allowed for startup, but generation requires a configured model or a model selected in the UI.

## Deferred

Autonomous file changes, approvals, agents, repository indexing, and tools remain out of scope until later phases.
