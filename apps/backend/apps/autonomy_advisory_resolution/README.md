# autonomy_advisory_resolution

Manual-first governance layer that tracks what happened after advisory notes were emitted by `autonomy_advisory`.

## Scope
- Consumes already emitted advisory artifacts.
- Tracks downstream resolution state (`PENDING`, `ACKNOWLEDGED`, `ADOPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`).
- Produces auditable runs/recommendations for operator review.

## Out of scope
- No broker/exchange execution.
- No opaque auto-apply to roadmap/scenario/program/manager.
- No auto-learning or black-box planner.
- Single-user local/paper/sandbox operations only.
