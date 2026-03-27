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

## Supervised autopilot (new)

`runbook_engine` now supports supervised, approval-aware auto-orchestration on top of existing runbook instances.

### New models
- `RunbookAutopilotRun`
- `RunbookAutopilotStepResult`
- `RunbookApprovalCheckpoint`

### Orchestration contract
- evaluate every step against `automation_policy`
- outcomes per step:
  - `AUTO_EXECUTED`
  - `APPROVAL_REQUIRED`
  - `MANUAL_ONLY`
  - `BLOCKED`
  - `FAILED`
  - `SKIPPED`
- pause/stop conditions are explicit and auditable
- resume and retry are explicit operator actions

### New endpoints
- `POST /api/runbooks/<id>/run-autopilot/`
- `GET /api/runbooks/autopilot-runs/`
- `GET /api/runbooks/autopilot-runs/<id>/`
- `POST /api/runbooks/autopilot-runs/<id>/resume/`
- `POST /api/runbooks/autopilot-runs/<id>/retry-step/<step_id>/`
- `GET /api/runbooks/autopilot-summary/`

Still out of scope: full autonomy, real money, real execution, opaque planner behavior.
