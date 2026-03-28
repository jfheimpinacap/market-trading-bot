# autonomy_roadmap

Global autonomy roadmap board that coordinates **cross-domain sequencing** for staged autonomy.

- Consumes domain posture from `autonomy_manager` and rollout stability from `autonomy_rollout`.
- Adds explicit `DomainDependency` rules (`requires_stable`, `blocks_if_degraded`, `recommended_before`, `incompatible_parallel`).
- Produces recommendation-first global plans (`AutonomyRoadmapPlan`) with optional bundles.
- Keeps **manual-first** apply behavior: roadmap does not apply transitions automatically.

## Scope

In scope: dependency-aware sequencing, blocked/frozen domain detection, auditable plan snapshots, and API/UI visibility.

Out of scope: multi-domain auto-promotion, real-money execution, opaque black-box planning, multi-user coordination.
