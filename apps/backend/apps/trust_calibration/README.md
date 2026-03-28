# trust_calibration

Recommendation-only governance loop that consolidates approval/autopilot feedback and produces conservative trust-tier tuning suggestions.

## Scope
- Consolidates approval outcomes, automation decisions, action logs, and incident aftermath.
- Computes explicit calibration metrics per action domain.
- Emits auditable recommendations and policy-tuning candidates.
- Never auto-applies policy changes.

## Endpoints
- `POST /api/trust-calibration/run/`
- `GET /api/trust-calibration/runs/`
- `GET /api/trust-calibration/runs/<id>/`
- `GET /api/trust-calibration/runs/<id>/report/`
- `GET /api/trust-calibration/recommendations/`
- `GET /api/trust-calibration/summary/`
- `GET /api/trust-calibration/feedback/`

## Safety stance
- Manual-first, recommendation-only by default.
- Paper/sandbox analytics only.
- No real execution and no automatic trust-tier mutation.
