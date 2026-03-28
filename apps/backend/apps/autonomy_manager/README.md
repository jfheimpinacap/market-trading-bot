# autonomy_manager

`autonomy_manager` introduces a domain-level autonomy governance layer above action-level `automation_policy`.

## What it does

- Defines operational `AutonomyDomain` groups with explicit action mappings.
- Tracks domain stage posture through `AutonomyStageState`.
- Consolidates evidence (trust calibration, rollout outcomes, incidents, approvals, certification posture).
- Emits auditable `AutonomyStageRecommendation` records.
- Creates manual-first `AutonomyStageTransition` proposals with explicit apply/rollback endpoints.
- Enforces explicit approval gates for higher-impact transitions (for example assisted -> supervised autopilot).

## What it does **not** do

- No real-money execution.
- No real broker execution.
- No opaque automatic promotion.
- No black-box planner.
- No multi-user workflows.

## Key API routes

- `GET /api/autonomy/domains/`
- `GET /api/autonomy/states/`
- `GET /api/autonomy/recommendations/`
- `POST /api/autonomy/run-review/`
- `POST /api/autonomy/transitions/<id>/apply/`
- `POST /api/autonomy/transitions/<id>/rollback/`
- `GET /api/autonomy/summary/`

## Service layout

- `services/domains.py`: domain catalog + action mapping + default envelopes.
- `services/evidence.py`: explicit evidence consolidation by domain.
- `services/recommendation.py`: deterministic stage recommendation engine.
- `services/transitions.py`: transition creation, apply, rollback and approval-gate checks.
- `services/envelopes.py`: envelope payload shaping.

## Integration stance

- `automation_policy` remains authoritative at `action_type` granularity.
- `autonomy_manager` provides domain-level posture and manual-first orchestration over multiple action rules.
- `policy_tuning`/`policy_rollout` remain detailed change/observation layers and feed evidence into domain-level recommendation logic.
