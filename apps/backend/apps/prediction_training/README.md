# prediction_training

Training/model-registry boundary for the prediction stack.

## Scope
- Offline dataset build from historical `MarketSnapshot` rows.
- Single initial label: `future_probability_up_24h`.
- Reproducible train/validation split (`random_state=42`).
- XGBoost binary model + sigmoid calibration.
- Model artifact registry with explicit activation.
- Runtime fallback remains in `prediction_agent` heuristics when no active model (or model load/predict fails).
- Model governance layer for heuristic-vs-artifact comparison (auditable recommendation only, no auto-switch).

## Management commands
- `python manage.py build_prediction_dataset --name manual_dataset --horizon-hours 24`
- `python manage.py train_prediction_model --dataset-run-id <id> --model-name xgboost_baseline`
- `python manage.py activate_prediction_model <artifact_id>`

## API
- `POST /api/prediction/train/build-dataset/`
- `POST /api/prediction/train/run/`
- `GET /api/prediction/train/runs/`
- `GET /api/prediction/train/runs/<id>/`
- `GET /api/prediction/train/summary/`
- `GET /api/prediction/models/`
- `POST /api/prediction/models/<id>/activate/`
- `GET /api/prediction/models/active/`
- `GET /api/prediction/model-profiles/`
- `POST /api/prediction/compare-models/`
- `GET /api/prediction/comparisons/`
- `GET /api/prediction/comparisons/<id>/`
- `GET /api/prediction/active-model-recommendation/`
- `GET /api/prediction/model-governance-summary/`

## Model governance quickstart
1. Build dataset and train at least one candidate artifact.
2. Activate candidate explicitly (manual operator action).
3. Run `POST /api/prediction/compare-models/` with:
   - `baseline_key` (`heuristic_baseline`, `narrative_weighted`, `market_momentum_weighted`, `active_model`, `artifact:<id>`)
   - `candidate_key` (same key format)
   - `profile_slug` (`conservative_model_eval`, `balanced_model_eval`, `strict_calibration_eval`)
   - `scope` (`demo_only`, `real_only`, `mixed`)
4. Inspect comparison metrics and recommendation via:
   - `/api/prediction/comparisons/`
   - `/api/prediction/active-model-recommendation/`
   - `/api/prediction/model-governance-summary/`

Primary metrics include accuracy, log loss, brier score, calibration error, edge hit rate, confidence usefulness, coverage, and failure count.

## Explicit non-goals
No real-money execution, no real order routing, no automatic model switching, no auto-retraining scheduler, no AutoML, no risk/policy/safety replacement.
