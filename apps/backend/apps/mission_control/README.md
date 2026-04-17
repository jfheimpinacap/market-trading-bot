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

## Prompt 311 (test console/export regression hardening)

- Regression fix only (backend): corrected execution exposure diagnostics wiring so status/export no longer fails on
  name/key/local-variable errors in provenance/release-audit blocks.
- Added canonical defaults + normalize helpers for:
  `execution_exposure_provenance_summary` and `execution_exposure_release_audit_summary`.
- Degrade-safe behavior now distinguishes:
  - **real zero** metrics (diagnostic available with zero counts),
  - **unavailable** diagnostics (`diagnostic_status=UNAVAILABLE`, summary text `UNAVAILABLE`),
  - **fallback/degraded** recovery (`diagnostic_unavailable=true` plus explicit reason codes).
- No policy changes, no threshold changes, no guardrail relaxation, no exposure matching changes, no new entry paths.
