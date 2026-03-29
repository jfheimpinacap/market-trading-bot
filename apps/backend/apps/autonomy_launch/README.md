# autonomy_launch

Formal preflight launch gate between `autonomy_scheduler` admission and `autonomy_campaign` start.

## Scope
- Evaluate admitted/ready campaigns for start readiness now.
- Persist auditable readiness snapshots and launch authorizations.
- Emit explicit launch recommendations (START_NOW / HOLD / WAIT / BLOCK / REQUIRE_APPROVAL).
- Keep flow manual-first: authorization/hold actions are explicit operator operations.

## Non-goals
- No real-money execution.
- No opaque mass auto-start orchestration.
- No distributed scheduler.
- No multi-user workflow complexity.
