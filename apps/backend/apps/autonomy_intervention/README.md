# autonomy_intervention

Manual-first gateway for active autonomy campaign interventions.

## Scope
- Consume autonomy operations recommendations/signals and convert them into explicit intervention requests.
- Validate whether a requested action is safe under current campaign/program/runtime posture.
- Execute manual intervention actions (`pause`, `resume`, `escalate`, `abort_review`, `continue_clearance`) with auditable outcomes.
- Preserve local-first, paper/sandbox-only boundaries.

## Out of scope
- Real broker/exchange execution.
- Automatic opaque remediation.
- Multi-user arbitration.
