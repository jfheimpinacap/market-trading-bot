# Risk demo / trade guard mock

`apps.risk_demo` adds a first local-first risk guard layer for demo paper trading.

## Scope of this app
- evaluate a proposed paper trade before execution
- return a deterministic demo verdict: `APPROVE`, `CAUTION`, or `BLOCK`
- persist recent assessments for traceability and admin inspection
- keep heuristics explainable and intentionally simple

## What it is not
- not a real risk engine
- not portfolio VaR
- not Kelly sizing
- not ML or provider-backed analytics
- not auto-trading or execution automation

## Main endpoint
- `POST /api/risk/assess-trade/`
- `GET /api/risk/assessments/` for recent persisted assessments

Example request:

```json
{
  "market_id": 1,
  "trade_type": "BUY",
  "side": "YES",
  "quantity": "10.0000"
}
```

Example response shape:

```json
{
  "assessment": {
    "decision": "CAUTION",
    "score": "61.00",
    "confidence": "0.73",
    "summary": "Trade is possible in the demo, but the guard found concentration and liquidity warnings.",
    "rationale": "The guard checks market tradability, estimated cost versus cash, existing market exposure, recent signal actionability, spread, and low-activity flags.",
    "warnings": [
      {
        "code": "LARGE_TRADE",
        "severity": "medium",
        "message": "This trade would use a large share of the demo cash balance."
      }
    ],
    "is_actionable": true
  }
}
```

## Heuristics in this stage
- insufficient cash for a buy -> `BLOCK`
- terminal market states -> `BLOCK`
- paused/inactive market -> `BLOCK`
- large trade cost relative to cash -> `CAUTION` or `BLOCK`
- existing concentration in the same market -> `CAUTION`
- wide spread, low liquidity, or low 24h activity -> `CAUTION`
- contradictory or non-actionable demo signals -> `CAUTION`
- small trade in an active market with acceptable context -> `APPROVE`

## Integration notes
- The app reuses `markets`, `paper_trading`, and `signals` data.
- Views stay thin; heuristics live under `services/assessment.py`.
- The current paper trade endpoint is not hard-blocked server-side yet. The frontend uses this app as a trade guard before calling `POST /api/paper/trades/`.
