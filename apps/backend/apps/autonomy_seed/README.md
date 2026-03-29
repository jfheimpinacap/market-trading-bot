# autonomy_seed

Manual-first adopted package registry that converts `autonomy_package_review` ADOPTED package resolutions into explicit, persistent planning seeds for the next cycle.

## Scope
- Consumes (does not replace) `autonomy_package_review` decisions.
- Registers auditable `GovernanceSeed` artifacts with clear target scopes.
- Generates recommendation-first run outputs (`SeedRun`, `SeedRecommendation`) before any manual registration action.
- Keeps roadmap/scenario/program/manager modules unchanged automatically.

## API
- `GET /api/autonomy-seed/candidates/`
- `POST /api/autonomy-seed/run-review/`
- `GET /api/autonomy-seed/seeds/`
- `GET /api/autonomy-seed/recommendations/`
- `GET /api/autonomy-seed/summary/`
- `POST /api/autonomy-seed/register/<package_id>/`
- `POST /api/autonomy-seed/acknowledge/<seed_id>/`

## Out of scope
- No real-money flows.
- No broker/exchange real execution.
- No opaque auto-apply into roadmap/scenario/program/manager.
- No black-box planner.
