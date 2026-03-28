# autonomy_rollout

Post-change monitoring layer for domain-level autonomy stage transitions.

- Starts from an already **APPLIED** `AutonomyStageTransition` (owned by `autonomy_manager`).
- Captures explicit baseline and post-change snapshots per domain/action scope.
- Produces recommendation-first outcomes (`KEEP_STAGE`, `REQUIRE_MORE_DATA`, `FREEZE_DOMAIN`, `ROLLBACK_STAGE`, etc.).
- Supports manual, auditable rollback through `approval_center` + `autonomy_manager` transition rollback.

This module is local-first, paper/sandbox-only, and does **not** execute real money operations.
