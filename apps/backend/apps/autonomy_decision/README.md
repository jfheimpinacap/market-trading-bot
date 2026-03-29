# autonomy_decision

Formal governance decision layer that converts `autonomy_planning_review` accepted proposals into persisted and auditable future-cycle decision artifacts.

## Scope
- consume `PlanningProposalResolution` in `ACCEPTED`
- derive decision candidates + recommendation queue
- register `GovernanceDecision` artifacts manually
- provide run-level decision review audit trail

## Out of scope
- no real money / broker exchange live execution
- no opaque auto-apply into roadmap/scenario/program/manager
- no black-box planner or enterprise multi-user orchestration
