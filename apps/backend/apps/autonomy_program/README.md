# autonomy_program

Program-level control tower for autonomy campaigns. It does not execute campaign steps.

## Responsibilities
- Consolidate global multi-campaign posture and safe concurrency capacity.
- Evaluate explicit concurrency rules (max active campaigns, incompatible domains, degraded/incident blocks).
- Build campaign health snapshots from campaign/checkpoint/approval/incident/rollout signals.
- Emit auditable recommendations (`PAUSE_CAMPAIGN`, `REORDER_QUEUE`, `HOLD_NEW_CAMPAIGNS`, etc.).
- Apply conservative pause gating (`BLOCKED` campaign state) with approval requests when configured.

## Out of scope
- Real-money execution.
- Opaque multi-campaign auto-orchestration.
- Mass auto-apply planner.
- Multi-user coordination.
