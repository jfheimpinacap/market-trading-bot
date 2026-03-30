# tuning_board

Governed tuning board that translates `evaluation_lab` quantitative findings into bounded, auditable, manual-first tuning proposals.

## Scope
- Consumes `EvaluationRuntimeRun` + metrics/recommendations/drift flags.
- Emits `TuningReviewRun`, `TuningProposal`, `TuningImpactHypothesis`, `TuningRecommendation`, and optional `TuningProposalBundle`.
- Never auto-applies thresholds/caps/weights and never retrains models.

## API
- `POST /api/tuning/run-review/`
- `GET /api/tuning/proposals/`
- `GET /api/tuning/hypotheses/`
- `GET /api/tuning/recommendations/`
- `GET /api/tuning/summary/`
- `GET /api/tuning/bundles/`
