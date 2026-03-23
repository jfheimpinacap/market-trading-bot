# Policy engine demo

The `apps.policy_engine` app adds a local-first approval layer on top of the existing risk demo and paper trading flow.

## Purpose
- convert a trade proposal into one explicit operational decision:
  - `AUTO_APPROVE`
  - `APPROVAL_REQUIRED`
  - `HARD_BLOCK`
- keep every decision explainable, persisted, and easy to audit
- reuse existing demo context from markets, paper trading, risk demo, and signals
- prepare the monorepo for future approval queues or semi-autonomous workflows without enabling them yet

## Main concepts
- `ApprovalDecision`: persisted result for one trade proposal evaluation
- matched rules: serialized list of the rules that influenced the outcome
- policy service: deterministic evaluation layer that translates context into an operational approval result

## Rule philosophy
This app does **not** replace `risk_demo`.

Instead:
- `risk_demo` remains the analytical trade guard
- `policy_engine` consumes the risk output when available
- `policy_engine` adds governance rules such as market operability, account availability, exposure concentration, automation thresholds, and manual approval requirements

## Current demo rules
Examples in the current implementation:
- market inactive, paused, closed, or otherwise non-operable -> `HARD_BLOCK`
- missing price context -> `HARD_BLOCK`
- linked risk decision `BLOCK` -> `HARD_BLOCK`
- buy proposal that consumes too much paper cash -> `APPROVAL_REQUIRED` or `HARD_BLOCK`
- already high concentration in the same market -> `APPROVAL_REQUIRED` or `HARD_BLOCK`
- linked risk decision `CAUTION` -> `APPROVAL_REQUIRED`
- latest signal not actionable -> `APPROVAL_REQUIRED`
- automation-originated trade above a threshold -> `APPROVAL_REQUIRED`
- otherwise a small trade in clean demo conditions -> `AUTO_APPROVE`

## API
- `POST /api/policy/evaluate-trade/`
- `GET /api/policy/decisions/`
- `GET /api/policy/summary/`

Example payload:

```json
{
  "market_id": 1,
  "trade_type": "BUY",
  "side": "YES",
  "quantity": "5.0000",
  "requested_price": "0.5400",
  "triggered_from": "market_detail",
  "requested_by": "user",
  "risk_assessment_id": 12
}
```

## Scope limits
Still out of scope by design:
- real autonomous agents
- auto-trading
- providers or brokers
- ML scoring
- multi-user approval queues
- real-time notifications
