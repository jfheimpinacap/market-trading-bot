# autonomy_scenario

`autonomy_scenario` is a simulation-only autonomy scenario lab that evaluates candidate bundles and sequences **before** any real transition is applied.

## Scope

- manual-first and recommendation-first only
- paper/sandbox-only, local-first
- no auto-apply, no real execution, no real money

## Responsibility boundaries

- `autonomy_roadmap`: builds global recommendation plans and candidate bundles.
- `autonomy_scenario`: runs comparative what-if simulations over candidate options.
- `autonomy_manager`: remains the only stage-transition apply layer.
- `autonomy_rollout`: remains the post-apply observation and rollback guidance layer.

## API

- `POST /api/autonomy-scenario/run/`
- `GET /api/autonomy-scenario/runs/`
- `GET /api/autonomy-scenario/runs/<id>/`
- `GET /api/autonomy-scenario/options/`
- `GET /api/autonomy-scenario/recommendations/`
- `GET /api/autonomy-scenario/summary/`
