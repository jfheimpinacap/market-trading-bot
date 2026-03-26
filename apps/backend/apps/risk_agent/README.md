# risk_agent

Risk agent refinement module for paper/demo-only operation.

## Scope
- Structured `RiskAssessment` records.
- Auditable `RiskSizingDecision` output.
- `PositionWatchRun` + `PositionWatchEvent` loop for open paper positions.

## Guardrails
- No real-money execution.
- No exchange-side stop-loss or exit execution.
- Does **not** replace policy/safety/runtime; it provides risk context and conservative sizing suggestions.
