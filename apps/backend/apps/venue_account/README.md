# venue_account

Sandbox-only external account mirror and reconciliation layer.

## Scope
- Mirrors external-like venue account state from internal paper + execution venue artifacts.
- Stores canonical snapshots for account, balances, positions, and orders.
- Runs parity/reconciliation between internal paper state and external mirror state.
- Emits explicit reconciliation issues and optional incident visibility for severe drift.

## Out of scope (this phase)
- Real broker/exchange connectivity.
- Real credentials, real orders, real capital.
- Live websocket account streams.
- Live reconciliation.

## Relationship with existing apps
- `broker_bridge`: source of intents.
- `execution_venue`: source of canonical payload/response contract.
- `execution_simulator` + `paper_trading`: internal state/fills used to derive mirror snapshots.
- `go_live_gate`: can consume reconciliation summaries as future readiness evidence.
- `incident_commander`: receives warnings when severe drift is detected.
