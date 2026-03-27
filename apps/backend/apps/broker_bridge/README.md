# broker_bridge

Sandbox/dry-run broker bridge layer that maps internal paper execution objects to broker-like order intents.

## Scope
- **Does**: intent mapping, validation against certification/runtime/safety/incidents, dry-run simulated broker response, readiness summary.
- **Does not**: real broker credentials, real order routing, real-money execution, websocket integrations, account reconciliation.

## Boundaries
- `execution_simulator` remains the paper execution source of truth.
- `broker_bridge` records what **would** be sent to a broker in a future phase.
- All routes are paper-only and local-first.
