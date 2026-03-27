# champion_challenger

Shadow benchmark supervisor for champion-vs-challenger stack validation in paper/demo mode.

## Scope

- Define explicit champion/challenger stack bindings.
- Run benchmark comparisons in shadow mode only.
- Compare opportunity/proposal/fill/performance deltas with execution-aware realism.
- Emit recommendation with rationale, without auto-switching.

## In scope

- `StackProfileBinding`
- `ChampionChallengerRun`
- `ShadowComparisonResult`
- Recommendation codes:
  - `KEEP_CHAMPION`
  - `CHALLENGER_PROMISING`
  - `CHALLENGER_UNDERPERFORMS`
  - `REVIEW_MANUALLY`

## Out of scope

- Real money
- Real execution
- Automatic champion switching
- Opaque planner / RL auto-optimization
