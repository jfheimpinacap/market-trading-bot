# autonomy_campaign

Formal campaign-orchestration layer for autonomy roadmap/scenario handoff into staged manual-first execution programs.

## Scope

- Creates explicit `AutonomyCampaign` programs from roadmap/scenario/manual inputs.
- Expands campaigns into ordered waves and domain steps.
- Uses checkpoints for approvals and rollout observation gates.
- Coordinates (does not replace) `autonomy_manager` transition apply and `autonomy_rollout` monitoring.
- Maintains recommendation-first, sandbox-only posture.

## Non-goals

- No real-money or live execution.
- No opaque auto-promotion planner.
- No mass auto-apply multi-domain promotion.
- No complex multi-user workflow.
