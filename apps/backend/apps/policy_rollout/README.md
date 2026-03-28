# policy_rollout

Policy rollout guard for post-change monitoring of applied `policy_tuning` candidates.

## Scope
- Opens an observation window after manual apply.
- Stores baseline + post-change snapshots.
- Compares deltas and emits recommendation-only outcomes (`KEEP_CHANGE`, `REQUIRE_MORE_DATA`, `ROLLBACK_CHANGE`, etc.).
- Supports manual rollback with explicit operator reason and optional approval gate.

## Non-goals
- No automatic rollback without explicit human confirmation.
- No real money / real execution integration.
- No opaque planner or black-box policy mutation.
