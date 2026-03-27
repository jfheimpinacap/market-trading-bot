# runbook_engine

`runbook_engine` provides structured, manual-first operator playbooks (runbooks) for incidents, degraded mode, rollout issues, certification downgrades, parity gaps, and queue pressure.

## Scope
- Defines reusable `RunbookTemplate` records.
- Instantiates auditable `RunbookInstance` workflows tied to source objects.
- Executes step-by-step actions while reusing existing services.
- Captures `RunbookActionResult` evidence for each step.
- Recommends templates using deterministic, explainable matching.

## Out of scope
- Real money or live execution.
- Fully automatic opaque remediation.
- Multi-user workflow orchestration.

## API
- `GET /api/runbooks/templates/`
- `GET /api/runbooks/`
- `GET /api/runbooks/<id>/`
- `POST /api/runbooks/create/`
- `POST /api/runbooks/<id>/run-step/<step_id>/`
- `POST /api/runbooks/<id>/complete/`
- `GET /api/runbooks/summary/`
- `GET /api/runbooks/recommendations/`
