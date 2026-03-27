# trace_explorer

`trace_explorer` is a local-first, paper/sandbox-only provenance layer that unifies traceability across existing modules without replacing them.

## What it does

- Defines trace primitives: `TraceRoot`, `TraceNode`, `TraceEdge`, and `TraceQueryRun`.
- Reconstructs end-to-end decision lineage by aggregating existing records from:
  - research / prediction / risk / signals / proposal / allocation
  - paper execution / broker bridge / execution venue / venue account
  - incidents + degraded mode
  - agent orchestrator runs/handoffs and memory precedent uses
- Produces compact provenance snapshots for UI audit and debugging.

## Scope

In scope:
- local-first trace query + snapshot APIs
- auditable query run history
- partial-trace handling (explicitly marked as partial)

Out of scope (by design):
- real-money execution
- live broker execution
- distributed graph infra
- opaque planner behavior
- multi-user enterprise observability
