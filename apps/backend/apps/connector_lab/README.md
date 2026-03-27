# Connector Lab

Connector Lab is the technical certification harness for future venue connectors/adapters.

## Scope

- Sandbox-only adapter qualification.
- Explicit case-based checks for capabilities, payload mapping, response normalization, account mirror, and reconciliation.
- Readiness recommendation generation (`SANDBOX_CERTIFIED`, `READ_ONLY_PREPARED`, etc.).

## Out of scope

- Real broker/exchange credentials.
- Real read-only/live connectivity.
- Real order routing or money movement.

## API

- `GET /api/connectors/cases/`
- `POST /api/connectors/run-qualification/`
- `GET /api/connectors/runs/`
- `GET /api/connectors/runs/<id>/`
- `GET /api/connectors/current-readiness/`
- `GET /api/connectors/summary/`
