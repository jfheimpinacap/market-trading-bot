# Rollout Manager

Formal rollout layer for paper/demo stack promotion.

## Scope
- Executes gradual stack transition after `promotion_committee` recommendations.
- Supports `SHADOW_ONLY`, `CANARY`, and `STAGED` routing modes.
- Applies explicit rollback guardrails and auditable decisions.
- Keeps operation local-first, single-user, and paper/demo only.

## Out of scope
- Real-money execution.
- Opaque auto-switching.
- Distributed enterprise rollout orchestration.
