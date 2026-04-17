# mission_control

Mission control adds a local-first autonomous operations loop over existing components. It does not replace `opportunity_supervisor`; it orchestrates periodic cycles and records auditable session/cycle/step traces.

Scope:
- Paper/demo only.
- No real-money execution.
- Runtime governor + safety guard remain authoritative.
- Explicit start/pause/resume/stop/run-cycle controls.

## Prompt 310 (execution exposure release audit)

- Added a backend-only, observability-first diagnostic layer for execution exposure freshness/validity:
  `execution_exposure_release_audit`.
- This layer answers: **"should this blocker still be blocking?"** for pre-creation suppressions.
- It reports blocker validity, freshness, session/scope alignment, and release-readiness **without** changing policy.
- No policy thresholds changed, no guardrails relaxed, no auto-release/cleanup/delete/close actions were introduced.
