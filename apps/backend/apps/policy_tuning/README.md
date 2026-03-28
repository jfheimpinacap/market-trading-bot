# Policy Tuning

`policy_tuning` materializes **trust calibration recommendations** into explicit, reviewable, manually applied policy tuning candidates.

## Responsibilities

- Convert `trust_calibration.TrustCalibrationRecommendation` into `PolicyTuningCandidate` + `PolicyChangeSet`.
- Provide a formal review flow (`APPROVE/REJECT/REQUIRE_MORE_EVIDENCE/DEFER`).
- Apply only approved candidates to `automation_policy.AutomationPolicyRule`.
- Persist before/after snapshots in `PolicyTuningApplicationLog` for auditability.

## Non-goals

- No auto-apply.
- No real-money or live execution changes.
- No black-box tuning.
- No multi-user workflow.

Everything remains local-first, single-user, paper/sandbox only.
