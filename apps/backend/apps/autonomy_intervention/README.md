# autonomy_intervention

<<<<<<< HEAD
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
=======
Manual-first autonomy intervention control layer for active autonomy campaigns.

## Scope

- Intake and persistence for intervention requests.
- Safe execution gateway for pause/resume/escalate/review-for-abort/clear-to-continue.
- Outcome and action audit trail.
- Summary/run review for intervention board.

## Out of scope

- No real broker/exchange execution.
- No opaque auto-remediation.
- No multi-user orchestration.
>>>>>>> origin/main
