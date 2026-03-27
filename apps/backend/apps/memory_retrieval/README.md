# memory_retrieval

Semantic memory + precedent retrieval layer for local-first paper/demo workflows.

## Scope
- Builds **MemoryDocument** entities from high-value sources (learning memory, postmortem board, reviews, replay, experiments, lifecycle).
- Generates local embeddings via `llm_local` and stores vectors on each document.
- Executes similarity retrieval and persists each query as a `MemoryRetrievalRun` + `RetrievedPrecedent` rows.
- Produces a simple case-based precedent summary for auditability.
- Provides conservative influence summaries for internal agents and records each use in `AgentPrecedentUse`.

## Precedent-aware integration contracts (new)

- Influence modes:
  - `context_only`
  - `caution_boost`
  - `confidence_adjust`
  - `rationale_only`
- New endpoints for auditability:
  - `GET /api/memory/precedent-uses/`
  - `GET /api/memory/precedent-uses/<id>/`
  - `GET /api/memory/influence-summary/`
- Assist endpoints in research/prediction/risk/postmortem now return influence + summary payloads.
- This layer is explicitly bounded: memory can enrich decisions and apply conservative caution, but does not become a standalone planner.

## Explicitly out of scope
- Real-money execution.
- Real exchange actions.
- Mandatory external vector DB / enterprise RAG stack.
- Opaque planner-based autonomous decision making.
