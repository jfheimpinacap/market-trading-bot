# memory_retrieval

Semantic memory + precedent retrieval layer for local-first paper/demo workflows.

## Scope
- Builds **MemoryDocument** entities from high-value sources (learning memory, postmortem board, reviews, replay, experiments, lifecycle).
- Generates local embeddings via `llm_local` and stores vectors on each document.
- Executes similarity retrieval and persists each query as a `MemoryRetrievalRun` + `RetrievedPrecedent` rows.
- Produces a simple case-based precedent summary for auditability.

## Explicitly out of scope
- Real-money execution.
- Real exchange actions.
- Mandatory external vector DB / enterprise RAG stack.
- Opaque planner-based autonomous decision making.
