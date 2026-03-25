# Allocation engine (demo)

Portfolio-aware allocation layer for paper/demo proposals.

## Scope
- ranks candidate proposals with explicit heuristics (score/confidence/policy/risk/exposure/provider/learning)
- applies conservative portfolio caps (cash reserve, per-run budget, per-market cap, max executions)
- persists auditable run + decision records
- never enables real-money execution

## Endpoints
- `POST /api/allocation/evaluate/`
- `POST /api/allocation/run/`
- `GET /api/allocation/runs/`
- `GET /api/allocation/runs/<id>/`
- `GET /api/allocation/summary/`
