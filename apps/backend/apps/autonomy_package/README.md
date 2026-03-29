# autonomy_package

Manual-first decision bundle registry for next-cycle planning seeds.

## Scope
- Consumes formal `GovernanceDecision` records from `autonomy_decision`.
- Groups compatible decisions into auditable `GovernancePackage` artifacts.
- Produces explicit package recommendations and package runs.
- Does **not** auto-apply roadmap/scenario/program/manager mutations.

## API
- `GET /api/autonomy-package/candidates/`
- `POST /api/autonomy-package/run-review/`
- `GET /api/autonomy-package/packages/`
- `GET /api/autonomy-package/recommendations/`
- `GET /api/autonomy-package/summary/`
- `POST /api/autonomy-package/register/<decision_id>/`
- `POST /api/autonomy-package/acknowledge/<id>/`
