# execution_simulator

Paper execution realism layer for `market-trading-bot`.

## Scope
- Paper/demo only order lifecycle simulation.
- Explicit `PaperOrder`, `PaperExecutionAttempt`, and `PaperFill` records.
- Realistic (but conservative) handling of full fill, partial fill, no fill, cancel, and expire paths.
- Separation between decision/intent and execution outcome.

## Out of scope
- Real money.
- Real exchange routing.
- Exchange APIs.
- Institutional-grade microstructure simulation.
