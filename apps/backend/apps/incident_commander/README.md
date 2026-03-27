# incident_commander

Formal incident commander layer for local-first paper/demo operations.

## Scope
- Detects operational incidents across mission_control, rollout, runtime/safety, provider sync, execution simulator, queue pressure, memory indexing, LLM availability, and notification delivery.
- Applies conservative and auditable mitigations via explicit `IncidentAction` records.
- Maintains a global degraded-mode snapshot (`DegradedModeState`) showing what is paused/disabled and why.
- Supports bounded self-healing via explicit `IncidentRecoveryRun` retries (e.g., alert rebuild, memory indexing retry).

## Out of scope
- Real-money execution.
- Real broker/exchange actions.
- Opaque self-healing chains without audit trace.
- Distributed cluster orchestration.

## API
- `GET /api/incidents/`
- `GET /api/incidents/<id>/`
- `GET /api/incidents/current-state/`
- `POST /api/incidents/run-detection/`
- `POST /api/incidents/<id>/mitigate/`
- `POST /api/incidents/<id>/resolve/`
- `GET /api/incidents/summary/`
