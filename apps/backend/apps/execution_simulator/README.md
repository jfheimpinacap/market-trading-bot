# execution_simulator

Paper execution realism layer for `market-trading-bot`.

## Scope
- Paper/demo only order lifecycle simulation.
- Explicit `PaperOrder`, `PaperExecutionAttempt`, and `PaperFill` records.
- Realistic (but conservative) handling of full fill, partial fill, no fill, cancel, and expire paths.
- Separation between decision/intent and execution outcome.
- Used by execution-aware replay/evaluation/readiness flows to reduce perfect-fill optimism.

## Integrated execution-aware bridge
- `replay_lab` can run with `execution_mode=execution_aware` and bind simulator policy profiles.
- `evaluation_lab` consumes simulator attempts to attach execution-adjusted snapshot metrics.
- `experiment_lab` compares naive vs execution-aware outputs with explicit execution drag.
- `readiness_lab` includes an execution realism impact summary and score penalty.

All integrations remain paper/demo only and local-first.

## Out of scope
- Real money.
- Real exchange routing.
- Exchange APIs.
- Institutional-grade microstructure simulation.
