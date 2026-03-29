# autonomy_planning_review

Manual-first planning proposal resolution tracker.

This module consumes `autonomy_intake.PlanningProposal` artifacts and tracks downstream review outcomes (`PENDING`, `ACKNOWLEDGED`, `ACCEPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`) without auto-applying roadmap/scenario/program/manager changes.

## Scope
- Candidate view of emitted/ready/acknowledged/blocked planning proposals.
- Auditable resolution records per planning proposal.
- Explicit recommendation stream for manual operator actions.
- Run-level summary snapshots for cockpit/trace-friendly governance reporting.

## Out of scope
- Real money/exchange execution.
- Opaque auto-apply into planning modules.
- Multi-user workflow orchestration.
