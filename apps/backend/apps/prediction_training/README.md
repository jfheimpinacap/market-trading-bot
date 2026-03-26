# prediction_training

Training/model-registry boundary for the prediction stack.

## Scope
- Offline dataset build from historical `MarketSnapshot` rows.
- Single initial label: `future_probability_up_24h`.
- Reproducible train/validation split (`random_state=42`).
- XGBoost binary model + sigmoid calibration.
- Model artifact registry with explicit activation.
- Runtime fallback remains in `prediction_agent` heuristics when no active model (or model load/predict fails).

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

## Explicit non-goals
No real-money execution, no real order routing, no auto-retraining scheduler, no AutoML, no risk/policy/safety replacement.
