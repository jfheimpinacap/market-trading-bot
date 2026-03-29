# autonomy_backlog

`autonomy_backlog` is a manual-first governance handoff layer that converts already acknowledged/adopted autonomy advisories into auditable future-cycle backlog items.

## Scope
- Consumes advisory + advisory resolution artifacts; does not replace those apps.
- Creates structured `GovernanceBacklogItem` records with explicit target scope and priority.
- Emits transparent recommendations and review runs (`BacklogRun`, `BacklogRecommendation`).
- Never auto-applies roadmap/scenario/program/manager changes.

## Out of scope
- No real-money execution.
- No broker/exchange execution.
- No opaque planner or autonomous apply loop.
- No multi-user orchestration.
