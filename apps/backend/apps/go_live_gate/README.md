# go_live_gate

`go_live_gate` introduces the final **pre-live rehearsal boundary** above `broker_bridge`.

## What it does
- Provides a formal gate state for pre-live readiness (still paper-only).
- Runs persisted pre-live checklists.
- Stores manual approval requests.
- Executes a final rehearsal run using an existing `BrokerOrderIntent` and `BrokerDryRun`.
- Applies an explicit **capital firewall** that blocks every live path by policy.

## What it does **not** do
- No real order submission.
- No live credentials.
- No real broker/exchange routing.
- No real money movement.
- No auto-enable live execution.

## Relationship with broker_bridge
- `broker_bridge` maps/validates/dry-runs broker-like intents.
- `go_live_gate` adds checklist + approval + firewall decisions on top of those intents.
