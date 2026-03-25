# llm_local

Local-first LLM integration layer for Ollama.

## Scope
- Local chat/generation via Ollama (`/api/chat`).
- Local embeddings via Ollama (`/api/embeddings`).
- Structured JSON outputs for proposal thesis, postmortem insights, and learning notes.
- Safe degradation (503 + `degraded=true`) when LLM is unavailable.

## Environment variables
- `LLM_ENABLED=true|false`
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_CHAT_MODEL=<your_model>`
- `OLLAMA_EMBED_MODEL=nomic-embed-text`
- `OLLAMA_TIMEOUT_SECONDS=30`

## Endpoints
- `GET /api/llm/status/`
- `POST /api/llm/proposal-thesis/`
- `POST /api/llm/postmortem-summary/`
- `POST /api/llm/learning-note/`
- `POST /api/llm/embed/`

## Safety boundaries (current stage)
- Does **not** execute real-money operations.
- Does **not** replace risk/policy/safety decisions.
- Does **not** enable autonomous LLM trading.
- Enrichment only: narrative, summary, and note generation.
