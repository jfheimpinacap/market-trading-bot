# certification_board

Operational certification board for **paper/demo-only** operations.

This app consolidates evidence from readiness, chaos/resilience, incidents, rollout, champion/challenger, promotion, runtime, safety, profile and portfolio governance into:

- `CertificationEvidenceSnapshot`
- `CertificationRecommendation` (materialized in `CertificationRun`)
- `OperatingEnvelope`
- `CertificationDecisionLog`

Manual-first design:

- `run-review` always produces an auditable recommendation.
- `apply/<id>/` is optional and conservative (safe runtime changes only).
- No real-money execution, no auto go-live.
