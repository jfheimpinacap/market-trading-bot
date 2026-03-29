# autonomy_operations

Runtime monitoring layer for active autonomy campaigns after activation/start handoff.

## Scope
- Observe active campaign runtime state (RUNNING/PAUSED/BLOCKED).
- Produce explicit runtime snapshots, attention signals, and operations recommendations.
- Keep manual-first operation: recommendations only, no opaque auto-remediation.

## Out of scope
- Real-money trading.
- Broker/exchange execution.
- Automatic pause/resume/abort orchestration.
- Multi-user/distributed scheduling.
