# Profile Manager (Adaptive Meta-Governance)

This module provides an auditable adaptive profile layer for paper/demo workflows.

## Responsibilities
- Build an operational state snapshot across portfolio/runtime/safety/readiness.
- Classify the current regime (`NORMAL`, `CAUTION`, `STRESSED`, `CONCENTRATED`, `DRAWDOWN_MODE`, `DEFENSIVE`, `BLOCKED`).
- Emit a `ProfileDecision` with target profiles for research/signals/opportunity supervisor/mission control/portfolio governor.
- Distinguish recommendation vs apply (`RECOMMEND_ONLY`, `APPLY_SAFE`, `APPLY_FORCED`).
- Respect runtime/safety/readiness as higher authority.

## Out of scope
- Real money or real execution.
- Opaque planner behavior.
- RL/ML meta-controller.
- Multi-user orchestration.
