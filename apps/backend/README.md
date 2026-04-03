# Backend Django API

Backend base for the `market-trading-bot` monorepo. This service is intentionally local-first and currently focuses on clean project structure, a practical prediction-market catalog, and a smooth local workflow.

## Current purpose
- Provide a modular Django + DRF API base inside the monorepo.
- Keep a stable local development setup for PostgreSQL, Redis, Celery, and the frontend.
- Expose a lightweight healthcheck at `/api/health/`.
- Provide a provider-agnostic market domain for catalog, metadata, rule text, snapshot history, and local simulation work.
- Make it easy to seed realistic demo data locally for admin and frontend development.
- Make the demo dataset feel alive locally without real provider integrations, trading, or websockets.
- Provide precedent-aware agent support via `memory_retrieval` with conservative and auditable influence on research/prediction/risk/signals/postmortem.

## Runtime governor downstream mode enforcement (new)

`apps.runtime_governor` now includes `mode_enforcement/` services to make global operating mode operational across downstream modules (instead of descriptive-only):

- service split:
  - `mode_enforcement/services/rules.py`
  - `mode_enforcement/services/module_impacts.py`
  - `mode_enforcement/services/enforcement.py`
  - `mode_enforcement/services/recommendation.py`
  - `mode_enforcement/services/run.py`
- auditable entities:
  - `GlobalModeEnforcementRun`
  - `GlobalModeModuleImpact`
  - `GlobalModeEnforcementDecision`
  - `GlobalModeEnforcementRecommendation`
- enforced integration points:
  - mission timing cadence
  - session admission capacity
  - portfolio exposure decision/apply path
  - autonomous trader execution intake
  - heartbeat runner cadence interval
  - recovery resume conservatism

Design guardrails remain unchanged: local-first, single-user, paper-only, no live broker/exchange order routing, no real-money execution, and no replacement of existing runtime/safety/portfolio authorities.

## Runtime feedback self-assessment layer (new)

`apps.runtime_governor` now includes a runtime feedback controller sublayer (`runtime_feedback/services/`) for conservative regime-level performance review:

- service split:
  - `runtime_feedback/services/performance.py`
  - `runtime_feedback/services/diagnostics.py`
  - `runtime_feedback/services/feedback.py`
  - `runtime_feedback/services/recommendation.py`
  - `runtime_feedback/services/run.py`
- auditable entities:
  - `RuntimeFeedbackRun`
  - `RuntimePerformanceSnapshot`
  - `RuntimeDiagnosticReview`
  - `RuntimeFeedbackDecision`
  - `RuntimeFeedbackRecommendation`
- API:
  - `POST /api/runtime-governor/run-runtime-feedback-review/`
  - `GET /api/runtime-governor/runtime-feedback-runs/`
  - `GET /api/runtime-governor/runtime-performance-snapshots/`
  - `GET /api/runtime-governor/runtime-diagnostic-reviews/`
  - `GET /api/runtime-governor/runtime-feedback-decisions/`
  - `GET /api/runtime-governor/runtime-feedback-recommendations/`
  - `GET /api/runtime-governor/runtime-feedback-summary/`
  - `POST /api/runtime-governor/apply-runtime-feedback-decision/<decision_id>/`

This review layer is recommendation-first and auditable. It feeds global posture tuning conservatively, does not replace operating mode / enforcement / health / recovery / admission / exposure authorities, and keeps paper-only, local-first boundaries.

## Runtime feedback apply bridge (new)

`apps.runtime_governor` now includes `runtime_feedback_apply/services/` to transform runtime feedback decisions into conservative, auditable mode actions:

- service split:
  - `runtime_feedback_apply/services/apply.py`
  - `runtime_feedback_apply/services/recommendation.py`
  - `runtime_feedback_apply/services/run.py`
- auditable entities:
  - `RuntimeFeedbackApplyRun`
  - `RuntimeFeedbackApplyDecision`
  - `RuntimeFeedbackApplyRecord`
  - `RuntimeFeedbackApplyRecommendation`
- API:
  - `POST /api/runtime-governor/run-runtime-feedback-apply-review/`
  - `POST /api/runtime-governor/apply-runtime-feedback-decision/<decision_id>/`
  - `GET /api/runtime-governor/runtime-feedback-apply-runs/`
  - `GET /api/runtime-governor/runtime-feedback-apply-decisions/`
  - `GET /api/runtime-governor/runtime-feedback-apply-records/`
  - `GET /api/runtime-governor/runtime-feedback-apply-recommendations/`
  - `GET /api/runtime-governor/runtime-feedback-apply-summary/`

This layer closes feedback → mode → enforcement without replacing `runtime_governor`, `mission_control`, `portfolio_governor`, `risk_agent`, `safety_guard`, or `incident_commander`. Boundaries remain strict: local-first, single-user, paper-only, no real money, no live routing.

## Runtime mode stabilization review (new)

`apps.runtime_governor` now includes a dedicated stabilization review layer for anti-flapping + dwell-aware transition diagnostics:

- service split:
  - `services/transition_snapshot.py`
  - `services/stability_review.py`
  - `services/transition_decision.py`
  - `services/recommendation.py`
  - `services/run.py`
- auditable entities:
  - `RuntimeModeStabilizationRun`
  - `RuntimeModeTransitionSnapshot`
  - `RuntimeModeStabilityReview`
  - `RuntimeModeTransitionDecision`
  - `RuntimeModeStabilizationRecommendation`
- API:
  - `POST /api/runtime-governor/run-mode-stabilization-review/`
  - `GET /api/runtime-governor/mode-stabilization-runs/`
  - `GET /api/runtime-governor/mode-transition-snapshots/`
  - `GET /api/runtime-governor/mode-stability-reviews/`
  - `GET /api/runtime-governor/mode-transition-decisions/`
  - `GET /api/runtime-governor/mode-stabilization-recommendations/`
  - `GET /api/runtime-governor/mode-stabilization-summary/`

This layer now includes real stabilized transition apply with explicit audit trail:

- new service: `services/apply_transition.py`
- new auditable entity: `RuntimeModeTransitionApplyRecord`
- new endpoints:
  - `POST /api/runtime-governor/apply-stabilized-mode-transition/<decision_id>/`
  - `GET /api/runtime-governor/mode-transition-apply-records/`
- optional conservative auto apply:
  - `POST /api/runtime-governor/run-mode-stabilization-review/` with `auto_apply_safe=true`
- enforcement refresh runs only when a mode switch is actually applied.

This does not replace operating mode, runtime feedback apply, or mode enforcement authorities. Scope remains local-first, single-user, paper-only, no real money/live routing.

## Mission control autonomous session runtime (new)

`apps.mission_control` now has an explicit persistent session runtime layer (paper-only):

- entities:
  - `AutonomousRuntimeSession`
  - `AutonomousRuntimeTick`
  - `AutonomousCadenceDecision`
  - `AutonomousCooldownState`
  - `AutonomousSessionRecommendation`
- service split:
  - `services/session_runtime/session.py`
  - `services/session_runtime/cadence.py`
  - `services/session_runtime/tick.py`
  - `services/session_runtime/recommendation.py`
  - `services/session_runtime/run.py`
- API:
  - `POST /api/mission-control/start-autonomous-session/`
  - `POST /api/mission-control/pause-autonomous-session/<session_id>/`
  - `POST /api/mission-control/resume-autonomous-session/<session_id>/`
  - `POST /api/mission-control/stop-autonomous-session/<session_id>/`
  - `POST /api/mission-control/run-autonomous-tick/<session_id>/`
  - `GET /api/mission-control/autonomous-sessions/`
  - `GET /api/mission-control/autonomous-ticks/`
  - `GET /api/mission-control/autonomous-cadence-decisions/`
  - `GET /api/mission-control/autonomous-session-recommendations/`
  - `GET /api/mission-control/autonomous-session-summary/`

This layer extends existing mission control and autonomous trader orchestration; it does not replace runtime/policy/safety/portfolio authorities.

## Mission control local heartbeat runner (new)

`apps.mission_control` now also includes a local autonomous heartbeat runner sublayer:

- service split:
  - `services/session_heartbeat/runner.py`
  - `services/session_heartbeat/due_tick.py`
  - `services/session_heartbeat/dispatch.py`
  - `services/session_heartbeat/recommendation.py`
  - `services/session_heartbeat/run.py`
- API:
  - `POST /api/mission-control/start-autonomous-runner/`
  - `POST /api/mission-control/pause-autonomous-runner/`
  - `POST /api/mission-control/resume-autonomous-runner/`
  - `POST /api/mission-control/stop-autonomous-runner/`
  - `POST /api/mission-control/run-autonomous-heartbeat/`
  - `GET /api/mission-control/autonomous-runner-state/`
  - `GET /api/mission-control/autonomous-heartbeat-runs/`
  - `GET /api/mission-control/autonomous-heartbeat-decisions/`
  - `GET /api/mission-control/autonomous-tick-dispatch-attempts/`
  - `GET /api/mission-control/autonomous-heartbeat-recommendations/`
  - `GET /api/mission-control/autonomous-heartbeat-summary/`

This layer only automates due-tick progression of existing autonomous sessions and preserves paper-only, local-first boundaries.

## Mission control governance review queue (new)

`apps.mission_control` now exposes a cross-layer **governance review queue** focused on pending manual triage only.

- service split:
  - `services/collect.py`
  - `services/prioritize.py`
  - `services/recommendation.py`
  - `services/run.py`
- auditable entities:
  - `GovernanceReviewQueueRun`
  - `GovernanceReviewItem`
  - `GovernanceReviewRecommendation`
- API:
  - `POST /api/mission-control/run-governance-review-queue/`
  - `GET /api/mission-control/governance-review-runs/`
  - `GET /api/mission-control/governance-review-items/`
  - `GET /api/mission-control/governance-review-recommendations/`
  - `GET /api/mission-control/governance-review-summary/`

This layer centralizes blocked/manual/deferred/advisory outputs from runtime_governor + mission_control + portfolio_governor, reduces operator friction, and stays paper-only. Resolution is now available only through explicit operator actions (see section below).

## Mission control governance manual-safe resolution (new)

`apps.mission_control` now adds explicit operator resolution on top of the governance queue:

- new service: `services/resolve.py`
- new auditable entity:
  - `GovernanceReviewResolution`
- resolution actions:
  - `APPLY_MANUAL_APPROVAL`
  - `KEEP_BLOCKED`
  - `DISMISS_AS_EXPECTED`
  - `REQUIRE_FOLLOWUP`
  - `RETRY_SAFE_APPLY` (only when a source-safe retry path exists)
- API:
  - `POST /api/mission-control/resolve-governance-review-item/<item_id>/`
  - `GET /api/mission-control/governance-review-resolutions/`

This completes the manual-safe operator intervention step while keeping boundaries unchanged: paper-only, no live trading, no real money, and no replacement of existing authorities.

## Mission control governance auto-resolution (low-risk only) (new)

`apps.mission_control` now includes `governance_auto_resolution/` to reduce operator load on simple and explicitly safe governance items:

- service split:
  - `governance_auto_resolution/services/eligibility.py`
  - `governance_auto_resolution/services/auto_resolve.py`
  - `governance_auto_resolution/services/run.py`
- auditable entities:
  - `GovernanceAutoResolutionRun`
  - `GovernanceAutoResolutionDecision`
  - `GovernanceAutoResolutionRecord`
- API:
  - `POST /api/mission-control/run-governance-auto-resolution/`
  - `GET /api/mission-control/governance-auto-resolution-runs/`
  - `GET /api/mission-control/governance-auto-resolution-decisions/`
  - `GET /api/mission-control/governance-auto-resolution-records/`
  - `GET /api/mission-control/governance-auto-resolution-summary/`
  - `POST /api/mission-control/apply-governance-auto-resolution/<decision_id>/` (optional/manual replay)

This layer is intentionally conservative: it only auto-resolves explicit low-risk cases (advisory dismiss, safe retry when source supports it, or follow-up deferral), remains paper-only, and does not replace manual governance resolution.

## Mission control session health governance (new)

`apps.mission_control` now includes a conservative health/anomaly/intervention layer for autonomous sessions:

- service split:
  - `services/session_health/health_snapshot.py`
  - `services/session_health/anomaly.py`
  - `services/session_health/intervention.py`
  - `services/session_health/recommendation.py`
  - `services/session_health/run.py`
- auditable entities:
  - `AutonomousSessionHealthRun`
  - `AutonomousSessionHealthSnapshot`
  - `AutonomousSessionAnomaly`
  - `AutonomousSessionInterventionDecision`
  - `AutonomousSessionInterventionRecord`
  - `AutonomousSessionHealthRecommendation`
- API:
  - `POST /api/mission-control/run-session-health-review/`
  - `GET /api/mission-control/session-health-runs/`
  - `GET /api/mission-control/session-health-snapshots/`
  - `GET /api/mission-control/session-anomalies/`
  - `GET /api/mission-control/session-intervention-decisions/`
  - `GET /api/mission-control/session-health-recommendations/`
  - `GET /api/mission-control/session-health-summary/`
  - `POST /api/mission-control/apply-session-intervention/<decision_id>/`

This layer does not replace session runtime control, heartbeat runner, timing policy, runtime governor, safety guard, or incident commander; it adds explicit health governance above them.

## Mission control session recovery review governance (new)

`apps.mission_control` now includes a conservative recovery/stabilization eligibility sublayer:

- service split:
  - `services/session_recovery/recovery_snapshot.py`
  - `services/session_recovery/recovery_blockers.py`
  - `services/session_recovery/resume.py`
  - `services/session_recovery/recommendation.py`
  - `services/session_recovery/run.py`
- auditable entities:
  - `AutonomousSessionRecoveryRun`
  - `AutonomousSessionRecoverySnapshot`
  - `AutonomousRecoveryBlocker`
  - `AutonomousResumeDecision`
  - `AutonomousResumeRecord`
  - `AutonomousSessionRecoveryRecommendation`
- API:
  - `POST /api/mission-control/run-session-recovery-review/`
  - `GET /api/mission-control/session-recovery-runs/`
  - `GET /api/mission-control/session-recovery-snapshots/`
  - `GET /api/mission-control/session-recovery-blockers/`
  - `GET /api/mission-control/session-resume-decisions/`
  - `GET /api/mission-control/session-resume-records/`
  - `POST /api/mission-control/apply-session-resume/<decision_id>/`
  - `GET /api/mission-control/session-recovery-recommendations/`
  - `GET /api/mission-control/session-recovery-summary/`
  - `run-session-recovery-review` accepts optional `auto_apply_safe` to auto-apply only truly safe resumes.

Resume apply remains conservative and paper-only: active blockers always block apply, monitor-only resume is explicit, and reintegration reuses existing timing policy + heartbeat runner without replacing them.

## Precedent-aware backend layer (new)

- Added `AgentPrecedentUse` for auditable agent-memory usage records.
- Added `memory_retrieval/services/assist.py` and `memory_retrieval/services/influence.py` to separate:
  - retrieval
  - precedent summary
  - influence suggestion
  - usage persistence
- New audit endpoints:
  - `GET /api/memory/precedent-uses/`
  - `GET /api/memory/precedent-uses/<id>/`
  - `GET /api/memory/influence-summary/`
- Existing assist endpoints for research/prediction/risk/postmortem now return influence metadata + summary (not only run IDs).
- Mission control can optionally refresh memory index on cadence (`run_memory_index_refresh_every_n_cycles`) and cycle details now mark precedent-aware mode.

## Prediction runtime review layer (new)

`apps.prediction_agent` now contains a runtime-hardening layer that sits between research triage and downstream risk/signals:

- auditable run entity: `PredictionRuntimeRun`
- runtime input entity: `PredictionRuntimeCandidate`
- calibrated assessment entity: `PredictionRuntimeAssessment`
- recommendation entity: `PredictionRuntimeRecommendation`

New endpoints:
- `POST /api/prediction/run-runtime-review/`
- `GET /api/prediction/runtime-candidates/`
- `GET /api/prediction/runtime-assessments/`
- `GET /api/prediction/runtime-assessments/<id>/`
- `GET /api/prediction/runtime-recommendations/`
- `GET /api/prediction/runtime-summary/`

Service split:
- `services/candidate_building.py`
- `services/model_runtime.py`
- `services/calibration.py` (runtime calibration helpers)
- `services/context_adjustment.py`
- `services/recommendation.py`
- `services/run.py`

Design boundaries:
- no auto model switching, no auto retraining, no LLM final authority
- recommendation-first handoff only
- risk/policy/safety remain the downstream authority

## Governed tuning validation layer (new)

`apps.experiment_lab` now includes a dedicated governed experiment board for validating `tuning_board` proposals before any manual adoption step.

Core entities:
- `TuningExperimentRun`
- `ExperimentCandidate`
- `TuningChampionChallengerComparison`
- `ExperimentPromotionRecommendation`

Service split:
- `services/candidate_building.py`
- `services/baseline_challenger.py`
- `services/tuning_comparison.py`
- `services/recommendation.py`
- `services/run.py`

Endpoints:
- `POST /api/experiments/run-tuning-validation/`
- `GET /api/experiments/tuning-candidates/`
- `GET /api/experiments/champion-challenger-comparisons/`
- `GET /api/experiments/promotion-recommendations/`
- `GET /api/experiments/tuning-validation-summary/`

Boundary guarantees:
- recommendation-first only (no auto-apply)
- paper/replay/evaluation evidence only
- no automatic champion promotion

## Promotion governance board layer (new)

`apps.promotion_committee` now includes a formal manual-adoption governance loop that sits **after** `experiment_lab` validation:

- `PromotionReviewCycleRun`: auditable run envelope for each governance review cycle.
- `PromotionCase`: formal adoption case per validated challenger/proposal.
- `PromotionEvidencePack`: consolidated quantitative + rationale evidence pack.
- `PromotionDecisionRecommendation`: explicit committee-facing recommendation output.

Service split:
- `services/case_building.py`
- `services/evidence_pack.py`
- `services/readiness.py`
- `services/recommendation.py`
- `services/run.py`

Endpoints:
- `POST /api/promotion/run-review/`
- `GET /api/promotion/cases/`
- `GET /api/promotion/evidence-packs/`
- `GET /api/promotion/recommendations/`
- `GET /api/promotion/summary/`

Boundary guarantees:
- no auto-promote
- no auto-apply
- no real-money execution
- validation evidence is translated into manual committee cases, not runtime mutation

## Internal structure

```text
apps/backend/
├── apps/
│   ├── agents/
│   ├── audit/
│   ├── common/
│   ├── health/
│   ├── markets/
│   ├── paper_trading/
│   └── proposal_engine/
├── config/
│   ├── api.py
│   ├── celery.py
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── .env.example
├── manage.py
└── requirements.txt
```

## Apps available today
- `apps.common`: shared technical building blocks like abstract models and simple shared tasks.
- `apps.health`: configuration-oriented health endpoint.
- `apps.markets`: provider, event, market, market snapshot, and market rule models plus demo seeding, simulation, admin tooling, and read-only API endpoints.
- `apps.paper_trading`: demo-only paper account, positions, trades, portfolio snapshots, valuation services, admin tooling, and basic write APIs for local investing flows.
- `apps.risk_demo`: demo-only trade guard layer that evaluates proposed paper trades with explainable heuristics before execution.
- `apps.signals`: demo-only signals + formal signal-fusion layer that consolidates research/prediction/risk into ranked opportunity board outputs and proposal gating.
- `apps.postmortem_demo`: demo-only trade review layer that generates post-trade reviews for executed paper trades using deterministic heuristics.
- `apps.agents`: placeholder app for future agent domain work.
- `apps.audit`: placeholder app for future audit and post-mortem work.
- `apps.policy_engine`: demo-only operational approval layer that translates trade context into `AUTO_APPROVE`, `APPROVAL_REQUIRED`, or `HARD_BLOCK`.
- `apps.proposal_engine`: demo-only trade proposal layer that consolidates market + signals + risk + policy + paper context into auditable `TradeProposal` records.
- `apps.semi_auto_demo`: conservative semi-autonomous demo orchestration layer for evaluate-only, guarded paper auto-execution, and pending manual approvals.
- `apps.experiment_lab`: strategy profile persistence plus experiment run orchestration across replay and evaluation, with normalized comparison outputs.
- `apps.prediction_training`: offline prediction dataset/training/model-registry plus model governance (heuristic-vs-artifact comparison + recommendation).
- `apps.research_agent`: narrative scan/research layer with RSS + Reddit + optional X/Twitter adapter ingestion, local LLM structured analysis, social normalization, heuristic market linking, and shortlist candidate generation for paper/demo workflows.
- `apps.position_manager`: position lifecycle manager / exit decision engine that governs open paper positions with HOLD/REDUCE/CLOSE/REVIEW_REQUIRED decisions and auditable exit plans.
- `apps.policy_rollout`: post-change rollout guard for applied policy-tuning candidates, with baseline/post snapshots, before/after delta comparison, recommendation-first outcomes, and manual rollback audit loop.
- `apps.autonomy_advisory`: advisory registry that consumes reviewed autonomy insights and emits auditable manual-first artifacts/notes with dedup, blockers, run summaries, and target routing visibility.

## Autonomy advisory layer (new)

`apps.autonomy_advisory` sits after `autonomy_insights` synthesis and before any manual downstream governance action:

- consumes reviewed `CampaignInsight` records
- computes advisory candidates and recommendation queue
- emits auditable artifacts (`EMITTED`, `BLOCKED`, `DUPLICATE_SKIPPED`, etc.)
- creates formal memory precedent notes when target is `memory`
- keeps roadmap/scenario/program/manager routing as note/stub emission only (no auto apply)

Endpoints:
- `GET /api/autonomy-advisory/candidates/`
- `POST /api/autonomy-advisory/run-review/`
- `GET /api/autonomy-advisory/artifacts/`
- `GET /api/autonomy-advisory/recommendations/`
- `GET /api/autonomy-advisory/summary/`
- `POST /api/autonomy-advisory/emit/<insight_id>/`


## Autonomy backlog board layer (new)

`apps.autonomy_backlog` sits after `autonomy_advisory_resolution` and creates a formal, auditable future-cycle planning handoff without mutating roadmap/scenario/program/manager automatically.

What it does:
- consumes `ADOPTED`/`ACKNOWLEDGED` advisory resolutions as candidates
- builds structured governance backlog items by target scope (`roadmap`, `scenario`, `program`, `manager`, `operator_review`)
- applies explicit dedup + transparent priority heuristics
- emits run-level recommendation artifacts (`CREATE`, `PRIORITIZE`, `SKIP_DUPLICATE`, `REQUIRE_MANUAL_BACKLOG_REVIEW`, `REORDER`)
- keeps all actions manual-first (`create`, `prioritize`, optional `defer`)

What it does not do:
- no opaque auto-apply to roadmap/scenario/program/manager
- no real broker/exchange execution
- no real-money operations

Endpoints:
- `GET /api/autonomy-backlog/candidates/`
- `POST /api/autonomy-backlog/run-review/`
- `GET /api/autonomy-backlog/items/`
- `GET /api/autonomy-backlog/recommendations/`
- `GET /api/autonomy-backlog/summary/`
- `POST /api/autonomy-backlog/create/<artifact_id>/`
- `POST /api/autonomy-backlog/prioritize/<item_id>/`
- `POST /api/autonomy-backlog/defer/<item_id>/`


## Autonomy intake board layer (new)

`apps.autonomy_intake` sits after `autonomy_backlog` and formalizes **backlog-to-planning proposals** while keeping manual-first apply governance.

What it does:
- consumes READY/PRIORITIZED `GovernanceBacklogItem` rows from `autonomy_backlog`
- maps backlog types to planning proposal artifacts (`ROADMAP_PROPOSAL`, `SCENARIO_PROPOSAL`, `PROGRAM_REVIEW_PROPOSAL`, `MANAGER_REVIEW_PROPOSAL`, `OPERATOR_REVIEW_PROPOSAL`)
- emits auditable `PlanningProposal`, `IntakeRecommendation`, and `IntakeRun` records
- provides recommendation-first run summaries and duplicate protection by `backlog_item + target_scope`

What it does not do:
- no auto-apply to roadmap/scenario/program/manager
- no broker/exchange execution
- no opaque planner/ML authority

Endpoints:
- `GET /api/autonomy-intake/candidates/`
- `POST /api/autonomy-intake/run-review/`
- `GET /api/autonomy-intake/proposals/`
- `GET /api/autonomy-intake/recommendations/`
- `GET /api/autonomy-intake/summary/`
- `POST /api/autonomy-intake/emit/<backlog_item_id>/`
- `POST /api/autonomy-intake/acknowledge/<proposal_id>/`

## Policy rollout guard layer (new)

`apps.policy_rollout` is intentionally adjacent to (not replacing) `policy_tuning` and `trust_calibration`:

- `policy_tuning` still owns create/review/apply change management.
- `trust_calibration` still owns broad trust-signal recommendation analytics.
- `policy_rollout` monitors the impact **after apply** for one candidate/run.

Endpoints:
- `POST /api/policy-rollout/start/`
- `GET /api/policy-rollout/runs/`
- `GET /api/policy-rollout/runs/<id>/`
- `POST /api/policy-rollout/runs/<id>/evaluate/`
- `POST /api/policy-rollout/runs/<id>/rollback/`
- `GET /api/policy-rollout/summary/`

Manual-first safeguards:
- no automatic rollback execution
- rollback requires explicit operator request + rationale
- optional approval-center request creation for rollback gate consistency
- paper/sandbox-only metadata markers are retained for auditability

## Markets app summary
The `apps.markets` app now provides a practical local catalog for prediction-market development without adding trading workflows or provider integrations.

Current market models:
- `Provider`
- `Event`
- `Market`
- `MarketSnapshot`
- `MarketRule`

Current market workflows:
- deterministic demo seeding via `seed_markets_demo`
- live-looking local simulation via `simulate_markets_tick`
- optional local looping via `simulate_markets_loop`

Current read-only market endpoints:
- `/api/markets/providers/`
- `/api/markets/events/`
- `/api/markets/`
- `/api/markets/<id>/`
- `/api/markets/system-summary/`


## Real market data (new, read-only)

The backend now supports **real market data ingestion in read-only mode** for:
- Kalshi
- Polymarket

Implemented boundaries:
- provider-agnostic adapter layer (`libs/provider-core`, `libs/provider-kalshi`, `libs/provider-polymarket`)
- manual ingestion commands:
  - `python manage.py ingest_kalshi_markets`
  - `python manage.py ingest_polymarket_markets`
- optional flags: `--limit`, `--active-only`, `--provider-market-id`, `--query`
- normalized persistence into existing `Provider`/`Event`/`Market` models plus basic `MarketSnapshot`
- explicit source separation: `source_type=demo` vs `source_type=real_read_only`

API filtering additions on `/api/markets/`:
- `provider`
- `status`
- `category`
- `active` / `is_active`
- `source_type`
- `is_demo`
- `is_real`
- `search`

Explicitly still out of scope:
- real trading auth
- order placement/execution
- real portfolio/positions
- websocket/polling auto-sync

## Paper trading app summary
The `apps.paper_trading` app provides the first backend base for demo investing with fictional money, using existing `Market` prices as the execution source of truth.

Current paper trading models:
- `PaperAccount`
- `PaperPosition`
- `PaperTrade`
- `PaperPortfolioSnapshot`

Current paper trading workflows:
- idempotent demo account seeding via `seed_paper_account`
- immediate demo trade execution via `POST /api/paper/trades/`
- mark-to-market refresh via `refresh_paper_portfolio` or `POST /api/paper/revalue/`
- account summary and exposure inspection via read endpoints and Django admin

Current paper trading endpoints:
- `/api/paper/account/`
- `/api/paper/positions/`
- `/api/paper/trades/`
- `/api/paper/summary/`
- `/api/paper/revalue/`
- `/api/paper/snapshots/`


## Paper trading on real-market data mode

The backend now supports **paper trading on real-market data** with strict boundary separation:

- **Market data source** can be `demo` or `real_read_only`.
- **Execution mode** remains `paper_demo_only` for all paper trades.
- Real markets are still read-only catalog data; no real auth, no real order placement, no real portfolio sync.

What is enabled now:
- `POST /api/paper/trades/` accepts `real_read_only` markets when they are paper-tradable.
- `POST /api/risk/assess-trade/`, `POST /api/policy/evaluate-trade/`, and `POST /api/proposals/generate/` work with real read-only markets.
- serializers expose explicit mode fields (`source_type`, `is_real_data`, `paper_tradable`, `execution_mode`) to avoid ambiguity.

Paper tradability guardrails:
- open + active market required
- paused/terminal market blocked
- missing valid yes/no/probability pricing blocked
- clear validation messages when blocked

Still out of scope:
- real execution/auth/order routing
- real balances/positions/portfolio
- websocket execution or continuous exchange sync

## Risk demo app summary
The `apps.risk_demo` app adds a first trade-guard boundary between market detail and paper trade execution without pretending to be a real risk engine.

Current risk demo model:
- `TradeRiskAssessment`

Current risk demo workflow:
- evaluate a proposed trade via `POST /api/risk/assess-trade/`
- persist recent assessments for admin and traceability
- reuse market status, paper account balances, open positions, liquidity, spread, activity, and demo signals as deterministic heuristics

Current risk demo endpoints:
- `/api/risk/assess-trade/`
- `/api/risk/assessments/`

Out of scope by design:
- real risk engine logic
- VaR / Kelly / auto-sizing
- broker or provider integrations
- automatic trade execution

## Policy engine demo app summary
The `apps.policy_engine` app adds the missing governance layer between analytical risk and paper trade execution.

Current policy engine model:
- `ApprovalDecision`

Current policy engine workflow:
- evaluate a proposed trade via `POST /api/policy/evaluate-trade/`
- persist the approval decision together with matched rules, rationale, recommendation, and linked risk/signal context
- translate `risk_demo` output into an operational decision instead of duplicating risk logic
- reuse paper account exposure, market operability, and automation thresholds as deterministic governance rules

Current policy engine endpoints:
- `/api/policy/evaluate-trade/`
- `/api/policy/decisions/`
- `/api/policy/summary/`

Operational decisions returned today:
- `AUTO_APPROVE`
- `APPROVAL_REQUIRED`
- `HARD_BLOCK`

Out of scope by design:
- multi-user approval queues
- autonomous execution
- ML-based policy scoring
- push notifications or realtime approval routing

## Proposal engine demo app summary
The `apps.proposal_engine` app consolidates demo market context, recent signals, risk guard output, policy decisions, and paper-account exposure into a single auditable proposal object for backend-first workflows.

Current proposal engine model:
- `TradeProposal`

Current proposal engine workflow:
- generate one proposal via `POST /api/proposals/generate/`
- compute direction (`BUY_YES`, `BUY_NO`, `HOLD`, `AVOID`) using clear local heuristics
- run `risk_demo` and `policy_engine` checks before persisting `is_actionable` and recommendation
- persist metadata linking signals, account context, and downstream assessment IDs

Current proposal engine endpoints:
- `/api/proposals/`
- `/api/proposals/<id>/`
- `/api/proposals/generate/`

Out of scope by design:
- frontend proposal UI
- auto-trading or batch autonomous generation
- real market data integrations
- ML/LLM decisioning
- complex approval queue orchestration



## Semi-auto demo app summary
The `apps.semi_auto_demo` app adds a conservative orchestration layer on top of proposal/risk/policy/paper-trading without duplicating policy logic.

Current semi-auto models:
- `SemiAutoRun`
- `PendingApproval`

Current semi-auto workflow:
- evaluate-only cycle that generates proposals and classifies outcomes without execution
- scan-and-execute cycle that only auto-executes strict `AUTO_APPROVE` + guardrail-compliant BUY paper proposals
- pending approval queue for `APPROVAL_REQUIRED`
- explicit block path for `HARD_BLOCK` and guardrail failures

Current semi-auto endpoints:
- `/api/semi-auto/evaluate/`
- `/api/semi-auto/run/`
- `/api/semi-auto/runs/`
- `/api/semi-auto/runs/<id>/`
- `/api/semi-auto/pending-approvals/`
- `/api/semi-auto/pending-approvals/<id>/approve/`
- `/api/semi-auto/pending-approvals/<id>/reject/`
- `/api/semi-auto/summary/`

Out of scope by design:
- real trading execution
- exchange auth

## Position lifecycle manager summary
The `apps.position_manager` app closes the paper lifecycle loop after entry:

- consumes open paper positions + latest risk watch events + prediction/research drift context
- emits explicit lifecycle decisions per position (`HOLD`, `REDUCE`, `CLOSE`, `REVIEW_REQUIRED`, `BLOCK_ADD`)
- produces one `PositionExitPlan` per decision with queue/auto-execute path and final recommended action
- honors runtime and safety authority before any paper close/reduce action
- routes constrained actions into operator queue for review

Endpoints:
- `/api/positions/run-lifecycle/`
- `/api/positions/lifecycle-runs/`
- `/api/positions/lifecycle-runs/<id>/`
- `/api/positions/decisions/`
- `/api/positions/summary/`

Explicit non-goals remain:
- no real-money execution
- no real exchange orders/stops
- no opaque planner/LLM as final authority
- autonomous background schedulers/workers
- websockets or complex concurrency

## Signals app summary
The `apps.signals` app adds the first demo-only bridge between market simulation, paper trading, and future automation architecture.

Current signals models:
- `MockAgent`
- `MarketSignal`
- `SignalRun`

Current signals workflows:
- idempotent mock-agent seeding via `seed_mock_agents`
- local heuristic signal generation via `generate_demo_signals`
- read-only signal browsing for the frontend and admin

Current signals endpoints:
- `/api/signals/`
- `/api/signals/<id>/`
- `/api/signals/agents/`
- `/api/signals/summary/`


## Post-mortem demo app summary
The `apps.postmortem_demo` app closes the first local review loop across markets, signals, risk demo, paper trading, and the frontend `/postmortem` workspace.

Current post-mortem model:
- `TradeReview`

Current post-mortem workflow:
- generate or refresh trade reviews with `python manage.py generate_trade_reviews`
- classify each executed paper trade as `FAVORABLE`, `NEUTRAL`, or `UNFAVORABLE` using explainable heuristics
- persist summary, rationale, lesson, recommendation, estimated outcome context, and links back to the original trade
- expose read-only review endpoints for the frontend and admin

Current post-mortem endpoints:
- `/api/reviews/`
- `/api/reviews/<id>/`
- `/api/reviews/summary/`

Out of scope by design:
- ML-based post-mortem analysis
- autonomous post-trade agents
- news-based attribution
- real-time streaming review generation

## Environment configuration
1. Copy the backend env file:
   ```bash
   cp apps/backend/.env.example apps/backend/.env
   ```
2. Adjust values if needed.

If you prefer the repo launcher, `python start.py setup` or `python start.py up` will create `apps/backend/.env` automatically when it is missing, using this template.

Main variables:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_SETTINGS_MODULE`
- `DJANGO_ENV`
- `APP_MODE`
- `DJANGO_TIME_ZONE`

## Install dependencies
From the repository root or from `apps/backend`, install the backend requirements in your Python environment:

```bash
pip install -r apps/backend/requirements.txt
```

## Local development flow
A clean local-first flow for this stage looks like this:

1. Start PostgreSQL and Redis.
2. Run migrations.
3. Seed demo market data.
4. Run one or more simulation ticks, or start the loop mode.
5. Start the backend server.
6. Open Django admin.
7. Inspect the read-only API.
8. Refresh the frontend and verify the dashboard plus market pages react to changing values.

## Recommended shortcut from the repo root

The preferred local-first workflow for this repository is now:

```bash
python start.py
```

Or, if you only want to prepare the backend without keeping servers attached:

```bash
python start.py setup --skip-frontend
```

Backend-related launcher commands:

```bash
python start.py setup --skip-frontend
python start.py backend
python start.py seed
python start.py simulate-tick
python start.py simulate-loop
```

Paper trading setup and refresh commands:

```bash
cd apps/backend
python manage.py seed_paper_account
python manage.py refresh_paper_portfolio
python manage.py generate_trade_reviews
```

What the launcher handles before running backend commands:

- creates `apps/backend/.env` from `apps/backend/.env.example` if needed
- creates `apps/backend/.venv` if it does not exist
- installs `requirements.txt` only when the dependency hash changes
- starts PostgreSQL and Redis unless `--skip-infra` is used
- runs `python manage.py migrate`
- auto-seeds the demo catalog during `up`, `setup`, and `backend` only when no markets exist yet
- starts the Django dev server in detached mode by default so the main launcher can return without opening extra consoles
- waits for `http://localhost:8000/api/health/` before reporting backend startup success
- stores launcher state so `python start.py down` can stop the backend later

Useful backend launcher variants:

```bash
python start.py backend
python start.py backend --separate-windows
python start.py backend --skip-infra
python start.py backend --skip-seed
```

### Run migrations
From `apps/backend`:

```bash
cd apps/backend
python manage.py migrate
```

If you later modify models and need a new migration:

```bash
cd apps/backend
python manage.py makemigrations markets
python manage.py migrate
```

### Seed demo data
Populate the local database with coherent demo catalog data:

```bash
cd apps/backend
python manage.py seed_markets_demo
```

Create the demo paper account after the market seed:

```bash
python manage.py seed_paper_account
```

What gets created right now:
- 2 demo providers
- 6 demo events
- 12 demo markets
- 72 demo snapshots
- 6 demo market rules

The seed is update-or-create based, so it is reasonably safe to run more than once during local development.

### Run the simulation tick
Apply one local simulation pass over the demo markets:

```bash
cd apps/backend
python manage.py simulate_markets_tick
```

Useful variants:

```bash
python manage.py simulate_markets_tick --dry-run
python manage.py simulate_markets_tick --limit 5
python manage.py simulate_markets_tick --seed 7
```

What the tick can change:
- `current_market_probability`
- `current_yes_price`
- `current_no_price`
- `liquidity`
- `volume_24h`
- `volume_total`
- `spread_bps`
- `status` in conservative scenarios
- fresh `MarketSnapshot` rows aligned with the updated market state

### Run the simulation loop
For a simple repeating local process:

```bash
cd apps/backend
python manage.py simulate_markets_loop --interval 10 --iterations 20
```

Continuous mode:

```bash
python manage.py simulate_markets_loop --interval 5
```

Stop continuous mode with `Ctrl+C`.

### Run the development server

```bash
cd apps/backend
python manage.py runserver
```

The API will be available on `http://localhost:8000/`.

## Admin workflow
Create a superuser if needed:

```bash
cd apps/backend
python manage.py createsuperuser
```

Then open:
- Admin: `http://localhost:8000/admin/`
- Health API: `http://localhost:8000/api/health/`

Recommended admin checks after seeding and simulation:
- open **Providers** and verify counts per provider
- open **Events** and review category/status coverage
- open **Markets** and inspect status badges, liquidity, snapshot counts, latest snapshot, and last simulation tick
- open a market detail page and review rule inlines plus the latest snapshots inline
- open **Market Snapshots** to verify recent time-series values and new simulated rows
- open **Paper Accounts** and confirm the demo account cash/equity fields update after trades
- open **Paper Positions** to inspect side, quantity, mark price, and unrealized PnL per market
- open **Paper Trades** to verify buy/sell history and linked market navigation
- open **Paper Portfolio Snapshots** to confirm account-level history is being captured

## API examples
Healthcheck:

```bash
curl http://localhost:8000/api/health/
```

Provider and event catalogs:

```bash
curl http://localhost:8000/api/markets/providers/
curl "http://localhost:8000/api/markets/events/?provider=polymarket&category=technology"
```

Market catalogs and detail:

```bash
curl http://localhost:8000/api/markets/
curl "http://localhost:8000/api/markets/?provider=kalshi&status=open&is_active=true&ordering=-current_market_probability"
curl http://localhost:8000/api/markets/1/
curl http://localhost:8000/api/markets/system-summary/
```

Suggested simulation verification:

```bash
curl http://localhost:8000/api/markets/system-summary/
python manage.py simulate_markets_tick
curl http://localhost:8000/api/markets/system-summary/
```

The second summary response should report a higher `total_snapshots` count after a live tick.

## Market endpoint behavior
### `GET /api/markets/providers/`
Returns providers with lightweight aggregate counts:
- `event_count`
- `market_count`

### `GET /api/markets/events/`
Read-only event catalog.

Supported filters:
- `provider`
- `status`
- `category`

### `GET /api/markets/`
Read-only market catalog for frontend listing views.

Supported filters:
- `provider`
- `category`
- `status`
- `is_active`
- `event`
- `search`

Supported ordering:
- `title`
- `created_at`
- `resolution_time`
- `current_market_probability`
- `liquidity`
- `volume_24h`

### `GET /api/markets/<id>/`
Returns a richer market detail payload with:
- nested event detail
- related rules
- recent snapshots

### `GET /api/markets/system-summary/`
Returns lightweight system totals for local dashboards.

## Simulation design choices
The simulation layer is intentionally conservative:
- only demo markets are eligible
- resolved/cancelled/archived markets are skipped
- open markets move the most
- paused markets mostly drift slightly and may occasionally reopen
- closed markets are nearly static and only move toward resolution states
- probabilities are clamped between `0.0100` and `0.9900`
- prices are derived from probability rather than simulated independently
- `volume_total` only increases
- the API stays unchanged so the existing frontend sees changes via refresh alone

This keeps the system maintainable and ready for later additions like a system page, launcher, signals, mock agents, and paper-trading layers.

## Settings layout
- `base.py` contains shared defaults, installed apps, middleware, DRF, CORS, PostgreSQL, Redis, and Celery defaults.
- `local.py` keeps local development behavior simple.
- `lite.py` enables lightweight local execution without Docker using SQLite.
- `test.py` uses SQLite and eager Celery execution for lightweight test runs.
- `production.py` is reserved as a minimal production profile for later hardening.

By default, `manage.py`, ASGI, WSGI, and Celery use `config.settings.local` unless `DJANGO_SETTINGS_MODULE` is provided explicitly.

### Full mode vs lite mode

- **Full mode:** `config.settings.local` (PostgreSQL + Redis, usually with Docker Compose).
- **Lite mode:** `config.settings.lite` (SQLite, Docker skipped, Redis optional/disabled).

Useful launcher commands:

```bash
python start.py --lite
python start.py setup --lite
python start.py up --lite
```

In lite mode, backend behavior stays local-first paper/demo only with reduced infra expectations.

## Local frontend integration
CORS is configured for local Vite defaults only:
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:4173`
- `http://127.0.0.1:4173`

Set `VITE_API_BASE_URL` in the frontend to the backend URL, typically `http://localhost:8000/api`.

## Testing
Run backend market tests with the dedicated test settings:

```bash
cd apps/backend
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps.markets
```

## What is intentionally not implemented yet
This stage does **not** add:
- real Kalshi or Polymarket integrations
- trading execution
- paper trading workflows
- orders, fills, positions, or portfolio state
- Celery-based sync pipelines
- websockets
- signals or agent workflows
- ML, forecasting, or advanced analytics dashboards

## Automation demo

The backend now includes `apps/automation_demo/`, a local-first orchestration layer for explicit user-triggered demo actions.

### Available endpoints

- `POST /api/automation/simulate-tick/`
- `POST /api/automation/generate-signals/`
- `POST /api/automation/revalue-portfolio/`
- `POST /api/automation/generate-trade-reviews/`
- `POST /api/automation/sync-demo-state/`
- `POST /api/automation/run-demo-cycle/`
- `GET /api/automation/runs/`
- `GET /api/automation/runs/<id>/`
- `GET /api/automation/summary/`

### Intentional scope

This layer reuses the existing simulation, signals, paper trading, and post-mortem services. It records `DemoAutomationRun` rows for traceability, but it does **not** enable auto-trading, schedulers, Celery orchestration, provider integrations, or autonomous background agents.


## Continuous demo loop app summary
The `apps.continuous_demo` app adds a local-first autonomous loop for controlled background demo operation without real execution.

Current continuous demo models:
- `ContinuousDemoSession`
- `ContinuousDemoCycleRun`
- `LoopRuntimeControl`

Current continuous demo workflow:
- start/pause/resume/stop managed loop sessions
- run one manual cycle on demand
- one RUNNING session at a time with cycle-level concurrency guard
- strict paper-only path by reusing `automation_demo` + `semi_auto_demo` services
- pending approvals are delegated to `semi_auto_demo.PendingApproval`

Current continuous demo endpoints:
- `/api/continuous-demo/start/`
- `/api/continuous-demo/stop/`
- `/api/continuous-demo/pause/`
- `/api/continuous-demo/resume/`
- `/api/continuous-demo/run-cycle/`
- `/api/continuous-demo/status/`
- `/api/continuous-demo/sessions/`
- `/api/continuous-demo/sessions/<id>/`
- `/api/continuous-demo/cycles/`
- `/api/continuous-demo/cycles/<id>/`
- `/api/continuous-demo/summary/`

Out of scope by design:
- real trading execution
- exchange credentials/authentication
- distributed schedulers and websocket orchestration


## Safety hardening layer (paper/demo only)

- New `apps.safety_guard` module adds explicit guardrails for operational safety.
- Includes configurable limits for exposure, session drawdown, auto-trade caps, cooldown thresholds, and kill switch behavior.
- `continuous_demo` and `semi_auto_demo` now consult safety state before auto execution.
- Critical/manual actions remain manual by design: kill switch enable/disable, cooldown reset, config updates, pending approval decisions.


## Evaluation lab app summary
The `apps.evaluation_lab` app adds a benchmark/evaluation harness to objectively measure autonomous paper/demo behavior before increasing system autonomy.

Current evaluation models:
- `EvaluationRun`
- `EvaluationMetricSet`

Current evaluation workflow:
- build an auditable run from an existing continuous demo session (`POST /api/evaluation/build-for-session/<session_id>/`)
- aggregate cross-module metrics from cycles, proposals, approvals, paper trades, post-mortem reviews, safety events, and portfolio snapshots
- expose run summaries and simple comparisons for operator review

Current evaluation endpoints:
- `/api/evaluation/summary/`
- `/api/evaluation/runs/`
- `/api/evaluation/runs/<id>/`
- `/api/evaluation/recent/`
- `/api/evaluation/comparison/?left_id=<id>&right_id=<id>`

Out of scope by design:
- strategy optimization/tuning
- ML/LLM scoring
- real-money execution

## Learning memory / adaptive heuristics demo app (new)

Se agregó `apps.learning_memory` como capa explícita de memoria operativa demo.

Incluye:
- modelos auditables `LearningMemoryEntry` y `LearningAdjustment`
- servicios de ingesta heurística desde postmortem/evaluation/safety
- rebuild deterministico vía command y endpoint
- API read-first para memory/adjustments/summary
- integración conservadora con `proposal_engine` y `risk_demo`

Comandos y endpoints clave:
- `python manage.py rebuild_learning_memory`
- `GET /api/learning/memory/`
- `GET /api/learning/adjustments/`
- `GET /api/learning/summary/`
- `POST /api/learning/rebuild/`


## Controlled learning loop integration (new)

Se integró `learning_memory` con `automation_demo` y `continuous_demo` sin rehacer arquitectura:

- `LearningRebuildRun` persiste cada rebuild con trazabilidad y métricas.
- `/api/automation/` incluye:
  - `POST /rebuild-learning-memory/`
  - `POST /run-full-learning-cycle/`
- `/api/learning/` incluye:
  - `GET /rebuild-runs/`
  - `GET /rebuild-runs/<id>/`
  - `GET /integration-status/`
- `continuous_demo` agrega settings conservadores para rebuild (`learning_rebuild_enabled`, `learning_rebuild_every_n_cycles`, `learning_rebuild_after_reviews`), desactivado por defecto.

Jerarquía operativa explícita:
- learning ajusta (heurístico, acotado)
- policy gobierna decisiones
- safety limita/puede frenar

Fuera de alcance: ML real, LLM local, ejecución real o dinero real.

## Real data refresh pipeline hardening (new)

A dedicated backend boundary now exists at `apps.real_data_sync` for hardened read-only provider refresh runs.

What it adds:
- persisted `ProviderSyncRun` audit model (`SUCCESS/PARTIAL/FAILED/RUNNING`)
- sync orchestration service that reuses existing provider adapters + normalization (`apps.markets.services.real_data_ingestion`)
- provider health/status view (`last_success`, `last_failed`, `consecutive_failures`, stale warning)
- API endpoints:
  - `POST /api/real-sync/run/`
  - `GET /api/real-sync/runs/`
  - `GET /api/real-sync/runs/<id>/`
  - `GET /api/real-sync/status/`
  - `GET /api/real-sync/summary/`
- management command:
  - `python manage.py sync_real_markets --provider kalshi`
  - `python manage.py sync_real_markets --provider polymarket --active-only --limit 100`
  - `python manage.py sync_real_markets --provider kalshi --market-id <id>`

Scope remains intentionally strict:
- read-only market-data refresh only
- no real exchange auth
- no real order execution
- no websocket/streaming sync


## Real-market autonomous paper scope
`apps.real_market_ops` introduces a conservative autonomous operation scope:
- source must remain `real_read_only`
- execution remains `paper_demo_only`
- stale/degraded provider status can hard-block eligibility
- insufficient pricing/liquidity/volume excludes markets
- every run is persisted as `RealMarketOperationRun` for auditability.

### API
- `POST /api/real-ops/evaluate/`
- `POST /api/real-ops/run/`
- `GET /api/real-ops/runs/`
- `GET /api/real-ops/runs/<id>/`
- `GET /api/real-ops/status/`
- `GET /api/real-ops/eligible-markets/` (supporting endpoint)

## Allocation engine demo (new)

Nuevo módulo `apps.allocation_engine` para priorización y reparto de capital paper a nivel portfolio.

Qué hace:
- toma propuestas ya generadas por `proposal_engine` (sin duplicar risk/policy/safety)
- rankea candidatos con heurísticas auditable (score/confidence/risk/policy/exposición/provider/learning)
- asigna `final_allocated_quantity` conservadora con límites por cash, corrida y mercado
- persiste `AllocationRun` + `AllocationDecision`

Integración:
- `semi_auto_demo` y `real_market_ops` pasan por allocation antes de autoejecutar paper trades
- mantiene ejecución `paper_demo_only`

Fuera de alcance:
- optimización cuantitativa avanzada, Kelly, ML/LLM, dinero real

## Operator queue app (new)

`apps.operator_queue` introduces a centralized manual exception inbox:
- `OperatorQueueItem`: approval/escalation items with source, type, priority, linked proposal/market/pending approval/trade.
- `OperatorDecisionLog`: auditable manual decisions (`APPROVE`, `REJECT`, `SNOOZE`, etc.).

Endpoints:
- `GET /api/operator-queue/`
- `GET /api/operator-queue/<id>/`
- `GET /api/operator-queue/summary/`
- `POST /api/operator-queue/<id>/approve/`
- `POST /api/operator-queue/<id>/reject/`
- `POST /api/operator-queue/<id>/snooze/`
- `POST /api/operator-queue/rebuild/`

Integration notes:
- semi-auto and real-ops now create queue items when they create `PendingApproval`.
- approving a queue item executes paper trade when executable context exists (directly or via linked `PendingApproval`).
- execution remains paper/demo only; no real order path is introduced.

## Replay lab (historical replay / backtest-like demo)

Nuevo app: `apps.replay_lab`.

Qué hace:
- Ejecuta replay histórico sobre `MarketSnapshot` persistidos (sin APIs externas en runtime).
- Recorre timeline cronológico por pasos (`ReplayStep`) y guarda corrida (`ReplayRun`).
- Reutiliza proposal/risk/policy/allocation/safety para decisiones, pero siempre en paper/demo only.
- Aísla portfolio con una cuenta paper dedicada por run (`replay-run-<id>`), evitando contaminar la cuenta operativa principal.

Endpoints:
- `POST /api/replay/run/`
- `GET /api/replay/runs/`
- `GET /api/replay/runs/<id>/`
- `GET /api/replay/summary/`
- `GET /api/replay/runs/<id>/steps/`

Límites intencionales:
- No execution real
- No slippage/order-book sofisticado
- No backtesting cuantitativo institucional
- No ML/LLM


## Experiment lab summary
The `apps.experiment_lab` app adds a clear experimentation boundary without duplicating replay/evaluation engines.

Models:
- `StrategyProfile`: persisted operational profile (type, market scope, config JSON)
- `ExperimentRun`: auditable run record linked to strategy profile and optional replay/evaluation/session entities

Services:
- `services/profiles.py`: base profile seed set (`Conservative`, `Balanced`, `Aggressive-light`, etc.)
- `services/runner.py`: applies profile config and orchestrates replay/evaluation calls
- `services/comparison.py`: run-vs-run metric deltas and simple interpretation text

Endpoints:
- `GET /api/experiments/profiles/`
- `GET /api/experiments/profiles/<id>/`
- `POST /api/experiments/run/`
- `GET /api/experiments/runs/`
- `GET /api/experiments/runs/<id>/`
- `GET /api/experiments/comparison/?left_run_id=<id>&right_run_id=<id>`
- `POST /api/experiments/seed-profiles/`
- `GET /api/experiments/summary/`

Out of scope remains unchanged: no real execution, no real money, no auto-tuning optimizer, no ML/LLM strategy training.

## Readiness lab app summary (new)

`apps.readiness_lab` adds an auditable promotion-gate layer above evaluation/replay/experiments:

- `ReadinessProfile`: configurable gate thresholds (conservative/balanced/strict/custom)
- `ReadinessAssessmentRun`: persisted readiness decisions (`READY`, `CAUTION`, `NOT_READY`)
- services split:
  - `services/assessment.py`: metrics aggregation + final decision
  - `services/gates.py`: reusable gate evaluation rules
  - `services/recommendations.py`: deterministic recommendation generation
  - `services/profiles.py`: base profile seeding

Main endpoints:
- `GET /api/readiness/profiles/`
- `GET /api/readiness/profiles/<id>/`
- `POST /api/readiness/assess/`
- `GET /api/readiness/runs/`
- `GET /api/readiness/runs/<id>/`
- `GET /api/readiness/summary/`
- `POST /api/readiness/seed-profiles/`

Boundary remains strict: readiness does not trigger real trading or automatic promotion.

## Runtime governor app (new)

`apps.runtime_governor` introduces explicit operational mode governance for runtime autonomy.

Key models:
- `RuntimeModeProfile`: capability profile for each runtime mode
- `RuntimeModeState`: persisted effective runtime mode and operational status
- `RuntimeTransitionLog`: audit log of mode transitions and degradations

Key endpoints:
- `GET /api/runtime/status/`
- `GET /api/runtime/modes/`
- `POST /api/runtime/set-mode/`
- `GET /api/runtime/transitions/`
- `GET /api/runtime/capabilities/`

Governance rules include:
- readiness-aware promotion limits (`NOT_READY` and `CAUTION` constraints)
- safety-forced degradation (`kill switch`, `hard stop`, cooldown/pause restrictions)
- conservative fallback to safer modes when constraints are violated

Integration:
- `semi_auto_demo`, `continuous_demo`, and `real_market_ops` now reconcile runtime mode before execution and respect runtime capabilities.
- everything remains paper/demo only.

## Operator alerts app (`apps.operator_alerts`)

A new backend boundary provides a local-first incident center for operator attention management.

### Models
- `OperatorAlert`: persistent, deduplicated operational alert records.
- `OperatorDigest`: persisted summary windows for recent activity.

### Services
- `services/alerts.py`: emit + dedupe + acknowledge + resolve + summary.
- `services/aggregation.py`: lightweight integration rules across queue/safety/runtime/sync/readiness/continuous-demo.
- `services/digest.py`: build digest snapshots from a chosen time window.

### Endpoints
- `GET /api/alerts/`
- `GET /api/alerts/<id>/`
- `GET /api/alerts/summary/`
- `POST /api/alerts/<id>/acknowledge/`
- `POST /api/alerts/<id>/resolve/`
- `GET /api/alerts/digests/`
- `GET /api/alerts/digests/<id>/`
- `POST /api/alerts/build-digest/`
- `POST /api/alerts/rebuild/`

### Scope and boundary
This layer is paper/demo only and focused on auditable exception handling. It intentionally excludes external push channels, enterprise workflow orchestration, and real execution controls.

## Notification center (delivery + escalation routing)

Nuevo módulo `apps.notification_center` para sacar alertas/digests del panel con reglas claras y trazabilidad:

- `NotificationChannel`: catálogo de canales configurables (`ui_only`, `webhook`, `email`; extensible a slack/telegram/discord sin activarlos todavía).
- `NotificationRule`: matching explícito (`match_criteria`), `delivery_mode` (`immediate`/`digest`), `severity_threshold`, `cooldown_seconds`, `dedupe_window_seconds`, canales target.
- `NotificationDelivery`: bitácora persistida por intento (`SENT`, `FAILED`, `SUPPRESSED`, etc.) con `reason`, payload resumido y metadata de respuesta.

Servicios (`apps/notification_center/services/`):
- `routing.py`: evaluación de reglas, canales y supresión por dedupe/cooldown.
- `delivery.py`: construcción de payload, dispatch por canal, registro de delivery.
- `channels.py`: bootstrap de canal `ui_only`.
- `summary.py`: salud y métricas de delivery.

Integración:
- `operator_alerts` sigue siendo SoT de incidentes.
- `notification_center` solo decide si/cuándo/cómo notificar.
- digests existentes (`OperatorDigest`) ahora pueden entregarse por `send-digest`.

## Notification automation layer (new)

`apps.notification_center` was extended with a small automation layer:

- `NotificationAutomationState`: global/local toggles and cadence limits
- `NotificationEscalationEvent`: auditable escalation reason log
- automatic alert dispatch hooks from `operator_alerts.emit_alert`
- digest automation via local cycle windows (`run_digest_cycle`)
- escalation cycle for persistent incidents (`run_escalation_cycle`)

New API endpoints:
- `GET /api/notifications/automation-status/`
- `POST /api/notifications/automation-enable/`
- `POST /api/notifications/automation-disable/`
- `POST /api/notifications/run-automatic-dispatch/`
- `POST /api/notifications/run-digest-cycle/`
- `GET /api/notifications/escalations/`

Design boundary: still local-first, paper/demo only, no real execution, no distributed orchestration.

## Local LLM integration (`apps.llm_local`, new)

A new backend app provides a clean local LLM boundary for Ollama:

- `clients/ollama.py`: reusable local chat client with timeout/error handling
- `clients/embeddings.py`: reusable embedding client (`nomic-embed-text` by default)
- `prompts/`: centralized prompt templates (`proposal.py`, `postmortem.py`, `learning.py`)
- `schemas.py`: structured JSON validation for thesis/insights/learning note payloads
- `services/`: task-level orchestration (`proposal_text`, `postmortem_text`, `learning_text`, `embeddings`, `status`)
- `views.py`: thin API layer with clean degradation (`503` + `degraded=true`)

Endpoints:
- `GET /api/llm/status/`
- `POST /api/llm/proposal-thesis/`
- `POST /api/llm/postmortem-summary/`
- `POST /api/llm/learning-note/`
- `POST /api/llm/embed/`

Environment variables:
- `LLM_ENABLED=true|false`
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_CHAT_MODEL=<model>`
- `OLLAMA_EMBED_MODEL=nomic-embed-text`
- `OLLAMA_TIMEOUT_SECONDS=30`

Important scope boundary:
- LLM enriches text and explanations only.
- Risk/policy/safety remain deterministic authorities.
- No real execution path is introduced.

## Research agent MVP (RSS-first narrative scan)

New app: `apps.research_agent`

Main entities:
- `NarrativeSource`
- `NarrativeItem`
- `NarrativeAnalysis`
- `MarketNarrativeLink`
- `ResearchCandidate`
- `ResearchScanRun`

Service split:
- `services/ingest.py`: RSS ingestion + dedupe persistence
- `services/analyze.py`: structured narrative extraction via local LLM + heuristic fallback
- `services/linking.py`: basic heuristic narrative-to-market linking
- `services/shortlist.py`: candidate scoring/ranking
- `services/scan.py`: orchestrated run with audit trace

API endpoints:
- `GET/POST /api/research/sources/`
- `POST /api/research/run-ingest/`
- `POST /api/research/run-analysis/`
- `GET /api/research/items/`
- `GET /api/research/items/<id>/`
- `GET /api/research/candidates/`
- `GET /api/research/summary/`

Boundary: paper/demo research support only; no real execution path.

## Prediction agent MVP (new)

Nueva app: `apps.prediction_agent`.

Responsabilidades:
- feature building auditable (`services/features.py`)
- profile registry (`services/profiles.py`)
- scoring + edge (`services/scoring.py`)
- calibración básica (`services/calibration.py`)

Modelos principales:
- `PredictionModelProfile`
- `PredictionRun`
- `PredictionFeatureSnapshot`
- `PredictionScore`
- `PredictionOutcomeLabel` (base para labels futuros)

Endpoints:
- `GET /api/prediction/profiles/`
- `POST /api/prediction/score-market/`
- `GET /api/prediction/scores/`
- `GET /api/prediction/scores/<id>/`
- `GET /api/prediction/summary/`
- `POST /api/prediction/build-features/`

Integración:
- `research_agent` aporta señales narrativas agregadas
- `learning_memory` aporta nudges conservadores
- `proposal_engine` consume el último score como contexto adicional (metadata + thesis/rationale)

Boundary:
- paper/demo only
- no ejecución real
- no XGBoost entrenado todavía (solo contrato y placeholder de perfil)

## Prediction training pipeline (new)

A new `apps.prediction_training` module provides an offline-first trained-model foundation without changing governance boundaries:

- dataset construction from historical `MarketSnapshot` rows
- initial label: `future_probability_up_24h` (binary direction at +24h horizon)
- reproducible train/validation split and persisted training runs
- XGBoost model training + explicit sigmoid calibration
- model artifact registry with active model switching
- prediction runtime fallback to heuristic scorer whenever no active trained model exists or inference fails

This remains paper/demo only and does not replace `risk_demo`, `policy_engine`, or `safety_guard`.

## Agents orchestration app (`apps.agents`)

`apps.agents` is now the explicit orchestration boundary for local-first, paper/demo-only agent workflows.

### Data model
- `AgentDefinition`: registry for enabled/disabled agents and schema versions
- `AgentRun`: per-agent execution trace
- `AgentPipelineRun`: end-to-end pipeline execution trace
- `AgentHandoff`: structured transfer record between agent runs

### Services
- `services/registry.py`: default agent registration bootstrap
- `services/orchestrator.py`: controlled pipeline runner + run lifecycle
- `services/pipelines.py`: pipeline implementations reusing existing domain services
- `services/handoffs.py`: handoff creation helper

### API
- `GET /api/agents/`
- `GET /api/agents/runs/`
- `GET /api/agents/runs/<id>/`
- `POST /api/agents/run-pipeline/`
- `GET /api/agents/pipelines/`
- `GET /api/agents/pipelines/<id>/`
- `GET /api/agents/handoffs/`
- `GET /api/agents/summary/`

### Current pipeline integration
- `research_to_prediction`: uses `research_agent` candidate outputs and `prediction_agent` scoring
- `postmortem_to_learning`: uses `postmortem_demo` review generation and `learning_memory` rebuild
- `real_market_agent_cycle`: uses read-only real markets through research → prediction → risk (paper/demo assessments only)

### Explicit scope guardrails
- no real money
- no real execution
- no opaque planner
- no autonomous black-box agent authority


## Risk agent refinement (paper/demo only)
- New `apps/backend/apps/risk_agent/` module introduces structured `RiskAssessment`, `RiskSizingDecision`, `PositionWatchRun`, and `PositionWatchEvent`.
- Separation of concerns is explicit: prediction estimates; risk evaluates/sizes; policy authorizes; safety limits; runtime governs mode.
- API endpoints: `POST /api/risk-agent/assess/`, `POST /api/risk-agent/size/`, `POST /api/risk-agent/run-watch/`, `GET /api/risk-agent/assessments/`, `GET /api/risk-agent/watch-events/`, `GET /api/risk-agent/summary/`.
- Frontend route `/risk-agent` provides assessment, sizing, watch loop, and audit history panels.
- Out of scope remains unchanged: no real money, no real execution, no production-grade Kelly optimizer, no exchange stop-loss automation.

## Postmortem board committee (new)

`apps.postmortem_agents` adds a structured, auditable multi-perspective postmortem layer on top of existing `postmortem_demo` reviews.

Perspectives in v1:
- narrative/research
- prediction
- risk/sizing
- runtime/safety/operator context
- learning synthesis

Key entities:
- `PostmortemBoardRun`
- `PostmortemAgentReview`
- `PostmortemBoardConclusion`

Backend endpoints:
- `POST /api/postmortem-board/run/`
- `GET /api/postmortem-board/runs/`
- `GET /api/postmortem-board/runs/<id>/`
- `GET /api/postmortem-board/reviews/`
- `GET /api/postmortem-board/conclusions/`
- `GET /api/postmortem-board/summary/`

LLM-local usage is optional and bounded: reviewers always start from structured context and degrade gracefully when Ollama is unavailable.

## Research universe scanner / triage board (new)

`apps.research_agent` now separates three backend responsibilities:

- `services/universe_scan.py`: explicit universe run orchestration + persisted run stats.
- `services/market_triage.py`: transparent eligibility/triage rules and profile thresholds.
- `services/pursuit_board.py`: board summary + pursuit candidate query surface.

New core entities:
- `MarketUniverseScanRun`
- `MarketTriageDecision`
- `PursuitCandidate`

New endpoints:
- `POST /api/research/run-universe-scan/`
- `GET /api/research/universe-scans/`
- `GET /api/research/universe-scans/<id>/`
- `GET /api/research/pursuit-candidates/`
- `GET /api/research/board-summary/`
- `POST /api/research/run-triage-to-prediction/`

Design boundary: no real-money paths and no real order execution are introduced.


## Signal fusion agent / opportunity board

The backend now adds a formal fusion boundary (`apps.signals`) that *reuses* research, prediction, and risk outputs instead of replacing them.

Flow:
- research triage/pursuit candidate -> prediction score -> risk assessment/sizing -> signal fusion -> proposal gate

Key properties:
- transparent weighted fusion with explicit profiles
- auditable status assignment (`WATCH`, `CANDIDATE`, `PROPOSAL_READY`, `BLOCKED`)
- explicit proposal gating before `proposal_engine`
- paper/demo-only invariants preserved (no real execution path added)

## Opportunity supervisor app (new)

`apps.opportunity_supervisor` introduces a formal supervisor boundary for scan-to-proposal-to-execution-path orchestration in paper/demo mode.

Main persisted entities:
- `OpportunityCycleRun`
- `OpportunityCycleItem`
- `OpportunityExecutionPlan`

Main API endpoints:
- `POST /api/opportunities/run-cycle/`
- `GET /api/opportunities/cycles/`
- `GET /api/opportunities/cycles/<id>/`
- `GET /api/opportunities/items/`
- `GET /api/opportunities/summary/`

Governance authority remains unchanged:
- runtime governor still controls auto-execution capabilities
- policy engine still controls approval class
- safety guard still controls overrides/blocking

No real execution was added.

## Mission control app (new)

`apps.mission_control` adds a transparent autonomous operations control plane on top of existing modules.

What it adds:
- `MissionControlState`, `MissionControlSession`, `MissionControlCycle`, `MissionControlStep`
- service boundaries:
  - `services/controller.py` for start/pause/resume/stop/status and loop threading
  - `services/cycle_runner.py` for explicit cycle sequencing and step audit records
  - `services/state.py` for singleton runtime state control
  - `services/profiles.py` for conservative cadence profiles
- API endpoints under `/api/mission-control/` for status, controls, sessions, cycles, and summary

What it does not add:
- real-money execution
- real exchange auth/order routing
- distributed enterprise scheduling

## Portfolio governor app summary

Nueva app `apps.portfolio_governor` para gobernanza agregada de cartera:

- Modelos:
  - `PortfolioExposureSnapshot`
  - `PortfolioThrottleDecision`
  - `PortfolioGovernanceRun`
- Servicios:
  - `services/exposure.py`
  - `services/regime.py`
  - `services/throttle.py`
  - `services/governance.py`
  - `services/profiles.py`
- Endpoints:
  - `POST /api/portfolio-governor/run-governance/`
  - `GET /api/portfolio-governor/runs/`
  - `GET /api/portfolio-governor/runs/<id>/`
  - `GET /api/portfolio-governor/exposure/`
  - `GET /api/portfolio-governor/throttle/`
  - `GET /api/portfolio-governor/summary/`

Diferencias de responsabilidades:
- `risk_agent`: riesgo/sizing por oportunidad/posición.
- `position_manager`: lifecycle por posición (hold/reduce/close/review).
- `portfolio_governor`: contexto agregado de cartera + gating/throttling de nuevas entradas.

Out of scope (todavía): real money, real execution, optimizer institucional, correlaciones de producción, hedging complejo.

## Profile manager (adaptive meta-governance)

New app: `apps.profile_manager`.

Purpose:
- aggregate runtime/safety/readiness + portfolio governor inputs
- classify operational regime
- recommend/apply module profile bundle in auditable form
- keep runtime/safety/readiness as top-level constraints

Key endpoints:
- `POST /api/profile-manager/run-governance/`
- `GET /api/profile-manager/runs/`
- `GET /api/profile-manager/runs/<id>/`
- `GET /api/profile-manager/current/`
- `GET /api/profile-manager/summary/`
- `POST /api/profile-manager/apply-decision/<id>/`

Scope remains strictly local-first, single-user, paper/demo only.

## Execution simulator
- New paper-only execution realism layer under `apps/backend/apps/execution_simulator` with explicit order lifecycle, attempts, and fills.
- Mission control, opportunity supervisor, and position manager can feed orders into this layer before portfolio impact is applied.

## Execution-aware replay / evaluation realism / readiness impact

The backend now integrates execution realism into historical and readiness workflows without enabling real execution.

- Replay (`/api/replay/run/`) accepts:
  - `execution_mode`: `naive` or `execution_aware`
  - `execution_profile`: `optimistic_paper`, `balanced_paper`, `conservative_paper`
- In `execution_aware` mode replay routes intent through `execution_simulator` order lifecycle (full/partial/no-fill, cancel/expire, slippage).
- Replay run `details` include `execution_impact_summary` (fill/no-fill/partial rates, slippage, execution-adjusted pnl, execution drag, realism score).
- Evaluation runs store `metadata.execution_adjusted_snapshot` so snapshots include execution realism impact.
- Experiment normalized metrics and comparison deltas now include execution-aware fields and naive-vs-aware drag where available.
- Readiness assessments include `details.execution_impact_summary` and apply a bounded execution realism penalty to avoid perfect-fill optimism.

Still out of scope: real money, exchange routing, institutional microstructure, and complex hedging.

## Champion-challenger app (new)

A new backend module `apps.champion_challenger` provides a clear shadow-benchmark boundary for paper/demo operation.

Core entities:
- `StackProfileBinding`: explicit stack snapshot (prediction model/profile + research/signal/opportunity/mission/portfolio profiles + execution profile + runtime constraints snapshot)
- `ChampionChallengerRun`: auditable run record for champion vs challenger
- `ShadowComparisonResult`: normalized side-by-side metrics and deltas

Service split:
- `services/bindings.py`: champion/challenger binding construction and champion selection
- `services/shadow_runner.py`: run shadow benchmark in isolated replay execution-aware mode
- `services/comparison.py`: consolidate benchmark metrics and deltas
- `services/recommendation.py`: recommendation code + reasons

API endpoints:
- `POST /api/champion-challenger/run/`
- `GET /api/champion-challenger/runs/`
- `GET /api/champion-challenger/runs/<id>/`
- `GET /api/champion-challenger/current-champion/`
- `GET /api/champion-challenger/summary/`
- `POST /api/champion-challenger/set-champion-binding/`

Integration notes:
- uses `prediction_training` active model registry as optional binding input
- uses `profile_manager` state/bindings for runtime-aware defaults
- can be triggered by `mission_control` every N cycles (`run_shadow_benchmark_every_n_cycles`)
- reuses execution-aware replay realism so comparison is not perfect-fill optimistic

Out of scope remains explicit: real-money execution, automatic champion promotion, opaque meta-controller.

## Semantic memory retrieval app (new)

`apps.memory_retrieval` introduces a formal semantic precedent layer for paper/demo workflows.

Responsibilities:
- index high-value documents from learning memory, postmortem board, trade reviews, replay, experiments, and lifecycle decisions
- create/update embeddings using existing local `llm_local` embedding service
- execute auditable precedent retrieval runs with persisted ranks and scores
- expose case-based summary (similar cases, caution signals, failure modes, lessons)

Design choices:
- local-first single-user operation
- no mandatory external vector DB
- no view-layer business logic (services split across documents/embeddings/indexing/retrieval/precedents)
- retrieval enriches decision context; it does not become final decision authority

## Promotion committee (new)

`apps.promotion_committee` introduces a formal stack-governance boundary above champion/challenger and readiness:

- `StackEvidenceSnapshot`: normalized evidence synthesis
- `PromotionReviewRun`: auditable recommendation run
- `PromotionDecisionLog`: recommendation/apply event trail

Services are intentionally split to keep logic out of views:
- `services/evidence.py`
- `services/recommendation.py`
- `services/review.py`
- `services/apply.py`
- `services/state.py`

API endpoints:
- `POST /api/promotion/run-review/`
- `GET /api/promotion/runs/`
- `GET /api/promotion/runs/<id>/`
- `GET /api/promotion/current-recommendation/`
- `GET /api/promotion/summary/`
- `POST /api/promotion/apply/<id>/`

Boundaries:
- paper/demo only
- manual-first
- no opaque auto-switching


## Rollout manager layer (new)

`apps.rollout_manager` adds the formal transition layer between committee recommendation and full promotion.

What it does:
- creates `StackRolloutPlan` records with champion/candidate bindings, mode, canary percentage, sampling rule, and guardrails
- starts and tracks `StackRolloutRun` lifecycle (`RUNNING`, `PAUSED`, `COMPLETED`, `ROLLED_BACK`, `FAILED`)
- evaluates explicit guardrails and persists `RolloutGuardrailEvent`
- emits auditable `RolloutDecision` recommendations
- applies explicit rollback to champion-only routing

API endpoints:
- `POST /api/rollout/create-plan/`
- `POST /api/rollout/start/<id>/`
- `POST /api/rollout/pause/<id>/`
- `POST /api/rollout/resume/<id>/`
- `POST /api/rollout/rollback/<id>/`
- `GET /api/rollout/runs/`
- `GET /api/rollout/runs/<id>/`
- `GET /api/rollout/current/`
- `GET /api/rollout/summary/`

Design boundary:
- `promotion_committee` still recommends
- `champion_challenger` still benchmarks
- `rollout_manager` executes gradual, reversible paper/demo transition

## Incident commander boundary (new)

New app: `apps/incident_commander`

Responsibilities:
- detect recurring operational incidents
- maintain incident lifecycle + action/recovery audit trail
- apply conservative degraded mode orchestration
- integrate with mission_control, rollout_manager, runtime_governor, safety_guard, operator_alerts, notification_center, and operator_queue

Key rule: runtime/safety remain higher authority; incident commander can only degrade conservatively, never bypass safety guardrails.

## Chaos lab / resilience validation (new)

A new backend app, `apps.chaos_lab`, adds a formal resilience-validation layer on top of existing runtime safety systems.

What it does:
- seeds a baseline catalog of controlled experiments
- runs fault injection in scoped/reversible mode
- triggers existing detection/mitigation flows from `incident_commander`
- records auditable observations + benchmark metrics
- cleans injected artifacts after each run to avoid persistent corruption

Key endpoints:
- `GET /api/chaos/experiments/`
- `POST /api/chaos/run/`
- `GET /api/chaos/runs/`
- `GET /api/chaos/runs/<id>/`
- `GET /api/chaos/benchmarks/`
- `GET /api/chaos/summary/`

Out of scope (unchanged): real money, real execution, unrestricted destructive chaos, cluster orchestration, opaque planner control.


## Operational certification board (paper-only)

New app: `apps.certification_board`.

Purpose:
- Consolidate evidence from readiness, chaos/resilience, incidents, champion-challenger, promotion, rollout, execution-aware evaluation, runtime/safety, portfolio governor and profile manager.
- Issue an auditable certification recommendation.
- Materialize an explicit paper-only `OperatingEnvelope`.

Key API endpoints:
- `POST /api/certification/run-review/`
- `GET /api/certification/runs/`
- `GET /api/certification/runs/<id>/`
- `GET /api/certification/current/`
- `GET /api/certification/summary/`
- `POST /api/certification/apply/<id>/` (optional manual safe apply)

Scope boundaries:
- manual-first and conservative
- no real money
- no real execution
- no opaque auto go-live


## Broker bridge sandbox layer (new)

`apps.broker_bridge` adds a dedicated real-execution-readiness boundary while preserving paper-only behavior.

Core entities:
- `BrokerOrderIntent`
- `BrokerBridgeValidation`
- `BrokerDryRun`

Core services:
- `services/intents.py`: build intents from internal sources
- `services/mapping.py`: map internal objects to broker-like fields/profiles
- `services/validation.py`: envelope/runtime/safety/incident guardrail checks
- `services/dry_run.py`: simulated broker routing response
- `services/readiness.py`: summary counters for operator UI

API:
- `POST /api/broker-bridge/create-intent/`
- `POST /api/broker-bridge/validate/<id>/`
- `POST /api/broker-bridge/dry-run/<id>/`
- `GET /api/broker-bridge/intents/`
- `GET /api/broker-bridge/intents/<id>/`
- `GET /api/broker-bridge/summary/`

Important boundary:
`broker_bridge` does not replace `execution_simulator`; it records what would be sent to a future broker adapter while execution remains paper-only.

## Go-live gate (rehearsal only)

A new backend app `apps/go_live_gate` adds the final pre-live rehearsal boundary **without enabling live execution**.

- API namespace: `/api/go-live/*`
- Core entities: `GoLiveChecklistRun`, `GoLiveApprovalRequest`, `GoLiveRehearsalRun`, `CapitalFirewallRule`
- Core behavior:
  - persisted pre-live checklist runs
  - manual approval requests (manual-first, never auto-applied)
  - final rehearsal run over an existing `BrokerOrderIntent`
  - explicit capital firewall that blocks all live transition paths

This layer sits above `broker_bridge`: it does not remap orders and does not send anything live.

## Execution venue app (new)

`apps.execution_venue` introduces the canonical broker/exchange-facing contract while keeping the existing paper-only boundary:

- `VenueOrderPayload`: stable external order schema mapped from `BrokerOrderIntent`
- `VenueOrderResponse`: normalized response envelope (`ACCEPTED`, `REJECTED`, `HOLD`, `REQUIRES_CONFIRMATION`, `UNSUPPORTED`, `INVALID_PAYLOAD`)
- `VenueCapabilityProfile`: adapter feature matrix + constraints, with `live_supported=false`
- `VenueParityRun`: auditable parity checks across broker bridge dry-run, execution simulator context, and sandbox adapter output

Default adapter is `NullSandboxVenueAdapter` (no real connectivity, no real order submission).

New endpoints:
- `GET /api/execution-venue/capabilities/`
- `POST /api/execution-venue/build-payload/<intent_id>/`
- `POST /api/execution-venue/dry-run/<intent_id>/`
- `POST /api/execution-venue/run-parity/<intent_id>/`
- `GET /api/execution-venue/parity-runs/`
- `GET /api/execution-venue/summary/`

## Venue account mirror module (new)

The backend now includes `apps.venue_account` as a dedicated sandbox external-state layer.

What it does:
- builds canonical snapshot entities:
  - `VenueAccountSnapshot`
  - `VenueBalanceSnapshot`
  - `VenueOrderSnapshot`
  - `VenuePositionSnapshot`
- runs formal parity checks via:
  - `VenueReconciliationRun`
  - `VenueReconciliationIssue`
- exposes REST endpoints under `/api/venue-account/*`.

How it differs from nearby modules:
- `execution_venue` = outgoing payload/response contract and send-parity harness.
- `venue_account` = incoming external-state mirror and account parity diagnostics.
- `broker_bridge` = intent/mapping/validation/dry-run source.

Still out of scope:
- real broker auth/connectivity
- live account sync
- live reconciliation
- real execution/money

## Connector Lab app (new)

`apps.connector_lab` is a technical adapter qualification harness that reuses `execution_venue`, `venue_account`, `go_live_gate`, `certification_board`, and `incident_commander` evidence surfaces while remaining strictly sandbox-only.

Service split:
- `services/cases.py`: explicit qualification catalog.
- `services/fixtures.py`: reusable sandbox fixture profiles.
- `services/qualification.py`: end-to-end suite execution against adapter contract + mirror/reconciliation.
- `services/recommendation.py`: readiness recommendation generation.
- `services/reporting.py`: summary aggregation for dashboards and gate/certification evidence.

Core endpoints:
- `GET /api/connectors/cases/`
- `POST /api/connectors/run-qualification/`
- `GET /api/connectors/runs/`
- `GET /api/connectors/runs/<id>/`
- `GET /api/connectors/current-readiness/`
- `GET /api/connectors/summary/`

Still out of scope:
- real read-only broker connectivity
- real credentials/secrets
- real order routing/execution
- real-money workflows

## Trace Explorer (`apps.trace_explorer`) (new)

A dedicated provenance app now unifies end-to-end traceability over existing modules.

### Purpose

`trace_explorer` does **not** replace existing domain modules. It aggregates them into a single auditable narrative:

- roots resolution (`TraceRoot`) by market/opportunity/proposal/order/incident/mission-cycle
- compact snapshots of related entities (`TraceNode`)
- explicit causal/handoff links (`TraceEdge`)
- query audit log (`TraceQueryRun`)

### Service split

- `services/roots.py`: root resolution and contextual ids
- `services/nodes.py`: node aggregation from existing modules (orchestrator, memory, execution, venue, incidents, profile/certification/runtime)
- `services/edges.py`: causal + handoff edges
- `services/provenance.py`: compact provenance snapshot
- `services/query.py`: end-to-end query orchestration + query-run persistence

### API

- `POST /api/trace/query/`
- `GET /api/trace/roots/`
- `GET /api/trace/roots/<id>/`
- `GET /api/trace/snapshot/<root_type>/<root_id>/`
- `GET /api/trace/query-runs/`
- `GET /api/trace/summary/`

### Scope boundaries

Included:
- local-first paper/sandbox provenance
- partial traces with explicit partial status
- auditable query history

Excluded:
- real execution and real money
- live broker connectors
- distributed graph infra
- opaque autonomous planner behavior


## runbook_engine

`apps.runbook_engine` adds a formal runbook/playbook layer on top of existing operations modules.

It provides:
- Structured templates (`RunbookTemplate`)
- Executable instances (`RunbookInstance`)
- Ordered guided steps (`RunbookStep`)
- Action evidence (`RunbookActionResult`)
- Deterministic recommendation matching

Key rule: manual-first orchestration with auditability. It reuses existing services and does not enable real/live execution.

## Automation policy matrix (new)

A new app, `apps.automation_policy`, introduces a formal trust-tiered automation boundary above existing operational actions and runbook steps.

Core capabilities:
- explicit profiles (`conservative_manual_first`, `balanced_assist`, `supervised_autopilot`)
- explicit trust tiers (`MANUAL_ONLY`, `APPROVAL_REQUIRED`, `SAFE_AUTOMATION`, `AUTO_BLOCKED`)
- rule matrix by `action_type` and optional `source_context_type`
- auditable decision records (`AutomationDecision`)
- explicit action execution logs (`AutomationActionLog`)
- guardrail-aware effective tier downgrade from runtime/safety/certification/degraded mode

API endpoints:
- `GET /api/automation-policy/profiles/`
- `GET /api/automation-policy/current/`
- `POST /api/automation-policy/evaluate/`
- `GET /api/automation-policy/decisions/`
- `GET /api/automation-policy/action-logs/`
- `POST /api/automation-policy/apply-profile/`
- `GET /api/automation-policy/summary/`

Boundary clarification:
- `runbook_engine` remains workflow orchestration.
- `automation_policy` decides if an action is auto-allowed, approval-required, manual-only, or blocked.
- `incident_commander`, `runtime_governor`, `safety_guard`, and `certification_board` remain higher-order authorities.
- scope remains local-first, single-user, paper/sandbox only.

## Runbook supervised autopilot / approval-aware orchestration (new)

The backend now extends `apps.runbook_engine` with a conservative autopilot layer:

- Models:
  - `RunbookAutopilotRun`
  - `RunbookAutopilotStepResult`
  - `RunbookApprovalCheckpoint`
- Services:
  - `runbook_engine.services.autopilot`
  - `runbook_engine.services.orchestration`
  - `runbook_engine.services.approvals`
  - `automation_policy.services.runbook_resolution`

Behavior:
- evaluate every step via `automation_policy`
- auto-execute only safe actions
- pause on approval/manual requirements
- block on guardrail/policy constraints
- support explicit resume and retry
- keep full step-level traceability via decisions + action logs + step results

New endpoints:
- `POST /api/runbooks/<id>/run-autopilot/`
- `GET /api/runbooks/autopilot-runs/`
- `GET /api/runbooks/autopilot-runs/<id>/`
- `POST /api/runbooks/autopilot-runs/<id>/resume/`
- `POST /api/runbooks/autopilot-runs/<id>/retry-step/<step_id>/`
- `GET /api/runbooks/autopilot-summary/`

Out of scope stays explicit: no live trading, no real execution venue actions, no fully autonomous black-box remediation.

## Approval center (new)

The backend now includes `apps.approval_center`, a lightweight unified human-in-the-loop decision layer.

What it does:
- aggregates approval requests from existing modules (without replacing their source models)
- normalizes lifecycle states: `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`, `ESCALATED`, `CANCELLED`
- stores explicit operator decisions in `ApprovalDecision`
- exposes impact previews before actioning
- routes decisions back to source workflows (e.g., runbook autopilot resume)

API endpoints:
- `GET /api/approvals/`
- `GET /api/approvals/pending/`
- `GET /api/approvals/summary/`
- `GET /api/approvals/<id>/`
- `POST /api/approvals/<id>/approve/`
- `POST /api/approvals/<id>/reject/`
- `POST /api/approvals/<id>/expire/`
- `POST /api/approvals/<id>/escalate/`

Scope guardrails:
- single-user local-first operation
- paper/sandbox only
- no live execution enablement


## Trust calibration / approval analytics layer

New app: `apps.trust_calibration`

Purpose:
- provide a formal approval analytics + human-feedback governance loop
- measure where `automation_policy` is too conservative/permissive
- generate recommendation-only trust-tier tuning suggestions

Key models:
- `TrustCalibrationRun`
- `AutomationFeedbackSnapshot`
- `TrustCalibrationRecommendation`

Service split:
- `services/feedback.py`: consolidates approval + automation + incident evidence
- `services/metrics.py`: explicit calibration metric formulas
- `services/recommendation.py`: conservative recommendation rules
- `services/candidates.py`: manual policy tuning candidate payloads
- `services/reporting.py`: summary views for cockpit/UI consumption

API:
- `POST /api/trust-calibration/run/`
- `GET /api/trust-calibration/runs/`
- `GET /api/trust-calibration/runs/<id>/`
- `GET /api/trust-calibration/recommendations/`
- `GET /api/trust-calibration/summary/`
- `GET /api/trust-calibration/feedback/`

Operational boundary remains unchanged:
- manual-first, recommendation-only default
- no automatic policy mutation
- no real execution / no real money

## Policy tuning board (new)

Added `apps.policy_tuning` as a formal recommendation-to-approval workflow layer.

- Source of truth for analysis stays in `trust_calibration`.
- Operational policy authority stays in `automation_policy`.
- `policy_tuning` materializes recommendation -> candidate -> review -> manual apply.
- Every apply writes before/after snapshots to `PolicyTuningApplicationLog`.
- No auto-apply, no real-money execution, no live execution.

API endpoints:
- `POST /api/policy-tuning/create-candidate/`
- `GET /api/policy-tuning/candidates/`
- `GET /api/policy-tuning/candidates/<id>/`
- `POST /api/policy-tuning/candidates/<id>/review/`
- `POST /api/policy-tuning/candidates/<id>/apply/`
- `GET /api/policy-tuning/application-logs/`
- `GET /api/policy-tuning/summary/`


## Autonomy manager layer (new)

A new `apps.autonomy_manager` app introduces a formal domain-level autonomy stage manager.

Responsibilities:
- domain catalog + action-type grouping (`AutonomyDomain`)
- stage posture state (`AutonomyStageState`)
- recommendation records (`AutonomyStageRecommendation`)
- manual-first transition records (`AutonomyStageTransition`)
- envelope constraints (`AutonomyEnvelope`)

It reuses existing governance modules instead of replacing them:
- `automation_policy` stays the granular authority per action type
- `trust_calibration` + `policy_rollout` provide evidence inputs
- `approval_center` gates high-impact stage changes
- `incident_commander`, `certification_board`, `trace_explorer`, and `cockpit` consume/emphasize posture context

Out-of-scope remains explicit: no real execution, no real money, no opaque automatic autonomy promotion.

## Autonomy rollout guard layer (new)

`apps.autonomy_rollout` complements `autonomy_manager` with post-change observation and rollback guidance for **domain stage transitions**.

- Starts from an **already applied** `AutonomyStageTransition`.
- Builds explicit baseline and post-change snapshots for domain action types.
- Compares before/after deltas (approval/friction/blocked/incident/degraded context).
- Emits recommendation-first outcomes: `KEEP_STAGE`, `REQUIRE_MORE_DATA`, `FREEZE_DOMAIN`, `ROLLBACK_STAGE`, `REVIEW_MANUALLY`, `STABILIZE_AND_MONITOR`.
- Supports manual rollback only, auditable, optionally approval-gated.

Endpoints:
- `POST /api/autonomy-rollout/start/`
- `GET /api/autonomy-rollout/runs/`
- `GET /api/autonomy-rollout/runs/<id>/`
- `POST /api/autonomy-rollout/runs/<id>/evaluate/`
- `POST /api/autonomy-rollout/runs/<id>/rollback/`
- `GET /api/autonomy-rollout/summary/`

Out of scope stays unchanged: no real-money execution, no auto-rollback without operator confirmation, no opaque planner.

## Autonomy roadmap layer (new)

`apps.autonomy_roadmap` adds global autonomy portfolio governance on top of domain-level governance:

- `autonomy_manager` remains the authority for per-domain transitions/apply/rollback.
- `autonomy_rollout` remains the post-change monitor for each applied transition.
- `autonomy_roadmap` consumes those signals and proposes **cross-domain sequencing**.

Core entities:
- `DomainDependency`
- `DomainRoadmapProfile` (criticality)
- `AutonomyRoadmapPlan`
- `RoadmapRecommendation`
- `RoadmapBundle`

Service split:
- `services/dependencies.py`: seed/list dependency graph + domain criticality
- `services/evidence.py`: aggregate posture from autonomy stage state, rollout status, incidents, approvals, trust, certification
- `services/recommendation.py`: recommendation-first draft generation (promote/hold/freeze/rollback/sequence/conflict)
- `services/bundles.py`: optional safe bundle suggestions with risk + approval hints
- `services/plans.py`: plan assembly and summary payloads

Boundary rules:
- recommendation-first and auditable only
- no hidden multi-domain auto-apply
- local-first, single-user, paper/sandbox only


## Autonomy scenario lab layer (new)

`apps.autonomy_scenario` complements (does not replace) autonomy roadmap and rollout:

- consumes roadmap dependencies + current stage posture + rollout warnings + trust/approval/incident summaries
- builds candidate options and compares them in simulation-only runs
- persists auditable run artifacts for operator review
- exposes recommendation-first API without applying transitions

Endpoints:
- `POST /api/autonomy-scenario/run/`
- `GET /api/autonomy-scenario/runs/`
- `GET /api/autonomy-scenario/runs/<id>/`
- `GET /api/autonomy-scenario/options/`
- `GET /api/autonomy-scenario/recommendations/`
- `GET /api/autonomy-scenario/summary/`

Out of scope remains explicit: no auto-apply, no real-money, no real execution, no opaque planner, no multi-user orchestration.


## Autonomy campaign layer (new)

`apps.autonomy_campaign` introduces the formal staged execution handoff between recommendation modules and manual transition apply.

Responsibilities:
- create campaigns from `autonomy_roadmap` plans or `autonomy_scenario` runs
- expand into wave/step programs with explicit status
- open checkpoints for approval and rollout-observation gates
- orchestrate `autonomy_manager` transition apply timing (without replacing transition logic)
- orchestrate `autonomy_rollout` monitor start + wait/evaluate checkpoints

Endpoints:
- `POST /api/autonomy-campaigns/create/`
- `GET /api/autonomy-campaigns/`
- `GET /api/autonomy-campaigns/<id>/`
- `POST /api/autonomy-campaigns/<id>/start/`
- `POST /api/autonomy-campaigns/<id>/resume/`
- `POST /api/autonomy-campaigns/<id>/abort/`
- `GET /api/autonomy-campaigns/summary/`

Boundaries:
- recommendation-first
- sandbox/paper only
- no real execution or auto mass multi-domain apply

## Autonomy program control tower (`autonomy_program`) (new)

A dedicated program-level layer now governs **multiple autonomy campaigns concurrently** without replacing per-campaign execution internals.

Scope:
- program posture/state consolidation (`active`, `blocked`, `observing`, `waiting approvals`, `degraded domains`, `locked domains`)
- explicit concurrency rules (max active campaigns, incompatible domains, degraded/incident/observation blocks)
- campaign health snapshots using campaign/checkpoint/approval/rollout/incident signals
- recommendation emission (`PAUSE_CAMPAIGN`, `REORDER_QUEUE`, `HOLD_NEW_CAMPAIGNS`, `SAFE_TO_START_NEXT`, `WAIT_FOR_STABILIZATION`)
- optional pause gating that marks campaign as `BLOCKED` and opens an approval-center request

Endpoints:
- `GET /api/autonomy-program/state/`
- `GET /api/autonomy-program/rules/`
- `POST /api/autonomy-program/run-review/`
- `GET /api/autonomy-program/recommendations/`
- `GET /api/autonomy-program/health/`
- `GET /api/autonomy-program/summary/`

Boundary guarantees:
- manual-first and recommendation-first
- paper/sandbox only
- no real-money or real-execution path
- no opaque multi-campaign auto-orchestration planner

## Autonomy scheduler (new)

A new backend module `apps.autonomy_scheduler` adds a formal campaign-admission layer between roadmap/scenario candidate generation and active program execution.

It introduces:
- `CampaignAdmission`: admission queue record per campaign (pending/ready/deferred/blocked/admitted/expired).
- `ChangeWindow`: safe-start windows with posture/domain constraints and admission capacity.
- `SchedulerRun`: auditable scheduler planning runs that snapshot queue/posture/window state.
- `AdmissionRecommendation`: explicit ADMIT/DEFER/HOLD/WAIT/BLOCK/REORDER recommendation records.

Core endpoints:
- `GET /api/autonomy-scheduler/queue/`
- `GET /api/autonomy-scheduler/windows/`
- `POST /api/autonomy-scheduler/run-plan/`
- `GET /api/autonomy-scheduler/recommendations/`
- `GET /api/autonomy-scheduler/summary/`
- `POST /api/autonomy-scheduler/admit/<campaign_id>/`
- `POST /api/autonomy-scheduler/defer/<campaign_id>/`

Design boundaries:
- keeps `autonomy_program` as authority for active campaign coexistence posture
- keeps `autonomy_campaign` as campaign execution engine (waves/steps/checkpoints)
- manual-first apply: no opaque auto-start or mass orchestration
- paper/sandbox only, local-first, single-user


## Autonomy launch app (new)

`apps.autonomy_launch` is a formal preflight start gate that complements existing autonomy layers:

- `autonomy_scheduler` still governs admission queue + windows
- `autonomy_program` still governs global concurrency posture
- `autonomy_campaign` still owns campaign execution (waves/steps/checkpoints)
- `autonomy_launch` adds **start authorization decisioning** for admitted campaigns

Core entities:
- `LaunchReadinessSnapshot`
- `LaunchAuthorization`
- `LaunchRun`
- `LaunchRecommendation`

Endpoints:
- `GET /api/autonomy-launch/candidates/`
- `POST /api/autonomy-launch/run-preflight/`
- `GET /api/autonomy-launch/readiness/`
- `GET /api/autonomy-launch/recommendations/`
- `GET /api/autonomy-launch/authorizations/`
- `GET /api/autonomy-launch/summary/`
- `POST /api/autonomy-launch/authorize/<campaign_id>/`
- `POST /api/autonomy-launch/hold/<campaign_id>/`

Non-goals remain explicit: no real-money execution, no opaque auto-start, no distributed scheduler, no multi-user complexity.

## Autonomy activation app (new)

`apps.autonomy_activation` is the formal authorized start handoff between `autonomy_launch` and `autonomy_campaign.start`.

Responsibilities:
- consume valid `LaunchAuthorization` records (`AUTHORIZED` only)
- revalidate dispatch constraints right before handoff (program posture, window state, conflicts, incidents, degraded pressure)
- execute explicit manual-first dispatch to campaign start
- persist auditable outcomes (`STARTED`, `BLOCKED`, `FAILED`, `EXPIRED`) in `CampaignActivation`
- maintain review snapshots (`ActivationRun`) and dispatch recommendations (`ActivationRecommendation`)

API:
- `GET /api/autonomy-activation/candidates/`
- `POST /api/autonomy-activation/run-dispatch-review/`
- `GET /api/autonomy-activation/recommendations/`
- `GET /api/autonomy-activation/activations/`
- `GET /api/autonomy-activation/summary/`
- `POST /api/autonomy-activation/dispatch/<campaign_id>/`

Out of scope (unchanged):
- real-money execution
- broker/exchange live dispatch
- opaque mass auto-start
- distributed orchestration

## Autonomy operations monitor layer (new)

Added `apps.autonomy_operations` as a focused runtime supervision boundary for **already started** campaigns.

Responsibilities:
- monitor active campaign runtime state (`RUNNING`/`PAUSED`/`BLOCKED`)
- persist `CampaignRuntimeSnapshot` rows with wave/step/checkpoint/progress/blockers pressure
- emit `CampaignAttentionSignal` entries (`OPEN`/`ACKNOWLEDGED`) for stalled/blocking/approval/incident/degraded/rollout pressure
- create auditable `OperationsRun` and `OperationsRecommendation` outputs

Endpoints:
- `GET /api/autonomy-operations/runtime/`
- `POST /api/autonomy-operations/run-monitor/`
- `GET /api/autonomy-operations/signals/`
- `GET /api/autonomy-operations/recommendations/`
- `GET /api/autonomy-operations/summary/`
- `POST /api/autonomy-operations/signals/<signal_id>/acknowledge/`

Service split:
- `services/runtime.py`: select active campaigns + build runtime context
- `services/progress.py`: progress score + stalled duration + runtime status classification
- `services/attention.py`: explicit signal generation
- `services/recommendation.py`: manual-first continue/pause/escalate/review guidance
- `services/control.py`: manual signal acknowledgment
- `services/run.py`: orchestrate snapshot + signals + recommendations + run summary

Boundary clarifications:
- does **not** replace `autonomy_campaign` execution
- does **not** replace `autonomy_activation` dispatch/start handoff
- does **not** replace `autonomy_program` posture authority
- recommendation-only/manual-first (no opaque auto-remediation)
- still paper/sandbox/local-first only


## Autonomy intervention architecture (new)

`apps.autonomy_intervention` sits between `autonomy_operations` recommendations and `autonomy_campaign` execution controls.

- `services/intake.py`: converts manual/operations-driven intent into `CampaignInterventionRequest`.
- `services/validation.py`: explicit intervention safety checks (campaign state, runtime blockers, incident pressure, program posture).
- `services/recommendation_bridge.py`: maps operations recommendations to intervention action intents.
- `services/execution.py`: executes manual actions (`pause`, `resume`, `escalate`, `abort_review`, `continue_clearance`) and persists action records.
- `services/outcome.py`: writes formal `InterventionOutcome` records for every execution.
- `services/run.py`: review run that bridges recommendations into requests and builds board-level summary metrics.

API surface:
- `GET /api/autonomy-interventions/requests/`
- `POST /api/autonomy-interventions/run-review/`
- `GET /api/autonomy-interventions/summary/`
- `POST /api/autonomy-interventions/request/<campaign_id>/`
- `POST /api/autonomy-interventions/execute/<request_id>/`
- `GET /api/autonomy-interventions/actions/`
- optional: request detail + cancel

## Autonomy recovery board (new)

Added `apps.autonomy_recovery` as the paused-campaign resolution layer that sits between interventions and final manual disposition.

Responsibilities:
- derive recovery candidates from paused/blocked/recently-intervened campaigns
- consolidate open blockers (approvals, checkpoints, incidents, program posture/domain locks)
- persist auditable `RecoverySnapshot`, `RecoveryRun`, and `RecoveryRecommendation`
- recommend explicit outcomes (`RESUME_CAMPAIGN`, `KEEP_PAUSED`, `REQUIRE_MORE_RECOVERY`, `REVIEW_FOR_ABORT`, `CLOSE_CAMPAIGN`, `REORDER_RECOVERY_PRIORITY`)
- expose manual approval request hooks for resume/close through `approval_center`

Key boundaries:
- does **not** execute campaign resume/abort itself (kept in intervention/campaign layers)
- does **not** replace `autonomy_operations` runtime monitor
- does **not** replace `autonomy_program` global posture authority
- stays paper/sandbox only, local-first, and manual-first

Endpoints:
- `GET /api/autonomy-recovery/candidates/`
- `POST /api/autonomy-recovery/run-review/`
- `GET /api/autonomy-recovery/snapshots/`
- `GET /api/autonomy-recovery/recommendations/`
- `GET /api/autonomy-recovery/summary/`
- `POST /api/autonomy-recovery/request-resume-approval/<campaign_id>/`
- `POST /api/autonomy-recovery/request-close-approval/<campaign_id>/`


## Autonomy disposition governance layer (new)

`apps.autonomy_disposition` formalizes the final campaign exit/disposition step after operations/intervention/recovery:

- models: `CampaignDisposition`, `DispositionRun`, `DispositionRecommendation`
- services: candidates, readiness, recommendation, apply, control, run
- endpoints:
  - `GET /api/autonomy-disposition/candidates/`
  - `POST /api/autonomy-disposition/run-review/`
  - `GET /api/autonomy-disposition/recommendations/`
  - `GET /api/autonomy-disposition/dispositions/`
  - `GET /api/autonomy-disposition/summary/`
  - `POST /api/autonomy-disposition/request-approval/<campaign_id>/`
  - `POST /api/autonomy-disposition/apply/<campaign_id>/`

Boundaries:
- manual-first, no opaque auto-close/abort/retire
- no real-money or live broker/exchange execution
- reuses recovery/intervention/operations/campaign/program context instead of replacing those layers


### Autonomy closeout board / campaign archive dossier (new)

The platform now includes `autonomy_closeout`, a post-disposition governance layer that converts final campaign outcomes into auditable closeout dossiers and reusable learning handoffs:

- consolidates post-disposition closeout candidates with explicit ready/blocked posture
- persists `CampaignCloseoutReport`, `CloseoutFinding`, `CloseoutRun`, and `CloseoutRecommendation`
- derives structured lifecycle/blocker/incident/intervention/recovery summaries
- emits explicit handoff stubs for `memory_retrieval`, `postmortem-board`, and roadmap/scenario feedback
- keeps completion manual-first (`POST /api/autonomy-closeout/complete/<campaign_id>/`) with blocker/approval checks

Boundaries:
- does **not** replace `autonomy_disposition` as final disposition authority
- does **not** auto-archive, auto-learn opaquely, or auto-apply roadmap changes
- remains local-first, single-user, and paper/sandbox only

## Autonomy followup governance layer (new)

`apps.autonomy_followup` formalizes post-closeout handoff emission without changing closeout ownership:

- `autonomy_closeout` remains the dossier/finding producer
- `autonomy_followup` consumes ready closeout reports and emits explicit followups
- dedup rules avoid repeated emission when linked artifacts already exist
- emitted artifacts are traceable and persisted:
  - memory document (`memory_retrieval.MemoryDocument`)
  - postmortem formal request stub (`approval_center.ApprovalRequest`)
  - roadmap/scenario feedback artifact id stub on closeout metadata

Main endpoints:
- `GET /api/autonomy-followup/candidates/`
- `POST /api/autonomy-followup/run-review/`
- `GET /api/autonomy-followup/followups/`
- `GET /api/autonomy-followup/recommendations/`
- `GET /api/autonomy-followup/summary/`
- `POST /api/autonomy-followup/emit/<campaign_id>/`

Scope remains manual-first, local-first, paper/sandbox only.

## Autonomy feedback governance layer (new)

`apps.autonomy_feedback` adds formal post-handoff resolution governance without replacing `autonomy_followup` emission.

Core entities:
- `FollowupResolution`: auditable per-followup downstream status and resolution decision.
- `FeedbackRun`: run-level consolidation counters (`pending`, `in_progress`, `completed`, `blocked`, `rejected`, `closed_loop`).
- `FeedbackRecommendation`: review/complete/pending/reorder guidance.

Endpoints:
- `GET /api/autonomy-feedback/candidates/`
- `POST /api/autonomy-feedback/run-review/`
- `GET /api/autonomy-feedback/resolutions/`
- `GET /api/autonomy-feedback/recommendations/`
- `GET /api/autonomy-feedback/summary/`
- `POST /api/autonomy-feedback/complete/<followup_id>/`

Safety boundary:
- manual-first only
- paper/sandbox scope only
- no auto-apply roadmap/scenario changes
- no opaque/black-box planner behavior

## Autonomy insights layer (new)

`apps.autonomy_insights` adds governance learning synthesis on top of the existing campaign closeout/followup/feedback loop.

What it does:
- consumes lifecycle evidence from `autonomy_closeout`, `autonomy_followup`, `autonomy_feedback`, plus disposition/findings metadata
- produces auditable cross-campaign insights (`CampaignInsight`)
- records deterministic run summaries (`InsightRun`)
- emits recommendation-first governance outputs (`InsightRecommendation`)

API:
- `GET /api/autonomy-insights/candidates/`
- `POST /api/autonomy-insights/run-review/`
- `GET /api/autonomy-insights/insights/`
- `GET /api/autonomy-insights/recommendations/`
- `GET /api/autonomy-insights/summary/`
- `GET /api/autonomy-insights/insights/<id>/`
- `POST /api/autonomy-insights/mark-reviewed/<id>/`

Hard boundaries:
- no auto-learning authority
- no automatic roadmap/scenario/program/manager apply
- no real-money or real broker/exchange execution


## Autonomy advisory resolution layer (new)

`apps.autonomy_advisory_resolution` is a dedicated post-emission governance tracker that complements `apps.autonomy_advisory`:

- `autonomy_advisory` continues to emit/deduplicate advisory artifacts
- `autonomy_advisory_resolution` consumes those emitted artifacts and tracks what happened after emission

Core entities:
- `AdvisoryResolution`
- `AdvisoryResolutionRun`
- `AdvisoryResolutionRecommendation`

Endpoints:
- `GET /api/autonomy-advisory-resolution/candidates/`
- `POST /api/autonomy-advisory-resolution/run-review/`
- `GET /api/autonomy-advisory-resolution/resolutions/`
- `GET /api/autonomy-advisory-resolution/recommendations/`
- `GET /api/autonomy-advisory-resolution/summary/`
- `POST /api/autonomy-advisory-resolution/acknowledge/<artifact_id>/`
- `POST /api/autonomy-advisory-resolution/adopt/<artifact_id>/`
- `POST /api/autonomy-advisory-resolution/defer/<artifact_id>/`
- `POST /api/autonomy-advisory-resolution/reject/<artifact_id>/`

Boundary: manual-first resolution tracking only; no auto-apply to downstream roadmap/scenario/program/manager modules.

## autonomy_planning_review backend module (new)

`apps.autonomy_planning_review` closes the planning handoff loop after `autonomy_intake` emission.

It **consumes existing `PlanningProposal` records** and adds an auditable downstream resolution layer:
- `PlanningProposalResolution` (`PENDING`, `ACKNOWLEDGED`, `ACCEPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`)
- `PlanningReviewRun`
- `PlanningReviewRecommendation`

It does **not** re-emit proposals and does **not** auto-apply roadmap/scenario/program/manager changes.

API endpoints:
- `GET /api/autonomy-planning-review/candidates/`
- `POST /api/autonomy-planning-review/run-review/`
- `GET /api/autonomy-planning-review/resolutions/`
- `GET /api/autonomy-planning-review/recommendations/`
- `GET /api/autonomy-planning-review/summary/`
- `POST /api/autonomy-planning-review/acknowledge/<proposal_id>/`
- `POST /api/autonomy-planning-review/accept/<proposal_id>/`
- `POST /api/autonomy-planning-review/defer/<proposal_id>/`
- `POST /api/autonomy-planning-review/reject/<proposal_id>/`

## `autonomy_decision` backend module (new)

`apps.autonomy_decision` formaliza el paso de `ACCEPTED planning proposals` a `GovernanceDecision` persistida y reusable para ciclos futuros.

Entidades:
- `GovernanceDecision`
- `DecisionRun`
- `DecisionRecommendation`

Servicios:
- `services/candidates.py`: selecciona ACCEPTED resolutions elegibles
- `services/dedup.py`: evita duplicados por `planning_proposal + target_scope`
- `services/recommendation.py`: emite recomendaciones explícitas de registro/manual review/reorder
- `services/registration.py`: crea artifacts de decisión persistidos
- `services/control.py`: acciones manual-first `register` / `acknowledge`
- `services/run.py`: consolidación de run auditable + recommendation summary

API mínima:
- `GET /api/autonomy-decision/candidates/`
- `POST /api/autonomy-decision/run-review/`
- `GET /api/autonomy-decision/decisions/`
- `GET /api/autonomy-decision/recommendations/`
- `GET /api/autonomy-decision/summary/`
- `POST /api/autonomy-decision/register/<proposal_id>/`
- `POST /api/autonomy-decision/acknowledge/<decision_id>/`

## `autonomy_package` backend module (new)

`apps.autonomy_package` consume decisiones formales registradas en `autonomy_decision` y las transforma en bundles/packages persistidos para el próximo ciclo de planificación.

### Qué hace
- genera candidatos de package desde `GovernanceDecision`
- aplica grouping transparente por `target_scope/grouping_key/priority`
- evita paquetes duplicados por `grouping_key + target_scope`
- emite recomendaciones de registro/manual review/priority reorder
- registra `GovernancePackage` sin mutar automáticamente roadmap/scenario/program/manager

### Endpoints
- `GET /api/autonomy-package/candidates/`
- `POST /api/autonomy-package/run-review/`
- `GET /api/autonomy-package/packages/`
- `GET /api/autonomy-package/recommendations/`
- `GET /api/autonomy-package/summary/`
- `POST /api/autonomy-package/register/<decision_id>/`
- `POST /api/autonomy-package/acknowledge/<id>/`

## Autonomy package review (`/api/autonomy-package-review/*`)

`autonomy_package_review` is the downstream resolution tracker for governance packages.

Scope:
- consumes bundles from `autonomy_package` (does not replace registration/dedup)
- persists `PackageResolution`, `PackageReviewRun`, and `PackageReviewRecommendation`
- keeps manual-first controls: acknowledge/adopt/defer/reject
- provides auditable summary and recommendation history

Core endpoints:
- `GET /api/autonomy-package-review/candidates/`
- `POST /api/autonomy-package-review/run-review/`
- `GET /api/autonomy-package-review/resolutions/`
- `GET /api/autonomy-package-review/recommendations/`
- `GET /api/autonomy-package-review/summary/`
- `POST /api/autonomy-package-review/acknowledge/<package_id>/`
- `POST /api/autonomy-package-review/adopt/<package_id>/`
- `POST /api/autonomy-package-review/defer/<package_id>/`
- `POST /api/autonomy-package-review/reject/<package_id>/`

Out of scope remains unchanged: real money, live broker execution, opaque auto-apply, enterprise multi-user orchestration.

## Autonomy seed layer (new)

`apps.autonomy_seed` provides the formal adopted-package-to-seed boundary for next-cycle planning.

What it does:
- consumes `autonomy_package_review.PackageResolution` records in `ADOPTED`
- derives seed candidates and emits recommendation-first run output
- registers persistent `GovernanceSeed` records manually (`POST /api/autonomy-seed/register/<package_id>/`)
- prevents duplicates by package + target scope
- keeps roadmap/scenario/program/manager untouched (seed artifact only)

Key endpoints:
- `GET /api/autonomy-seed/candidates/`
- `POST /api/autonomy-seed/run-review/`
- `GET /api/autonomy-seed/seeds/`
- `GET /api/autonomy-seed/recommendations/`
- `GET /api/autonomy-seed/summary/`
- `POST /api/autonomy-seed/register/<package_id>/`
- `POST /api/autonomy-seed/acknowledge/<seed_id>/`

Non-goals:
- no real broker/exchange execution
- no real-money execution
- no opaque auto-apply to roadmap/scenario/program/manager

## Autonomy seed review board layer (new)

`apps.autonomy_seed_review` closes the seed handoff loop after `apps.autonomy_seed` registration.

What it does:
- consumes existing `GovernanceSeed` rows (does not register or deduplicate seeds)
- persists auditable `SeedResolution` outcomes (`PENDING`, `ACKNOWLEDGED`, `ACCEPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`)
- emits `SeedReviewRecommendation` guidance and run snapshots (`SeedReviewRun`)
- supports manual-first actions: acknowledge/accept/defer/reject

What it does not do:
- no auto-apply into roadmap/scenario/program/manager
- no real broker/exchange execution
- no opaque planner/ML authority

Endpoints:
- `GET /api/autonomy-seed-review/candidates/`
- `POST /api/autonomy-seed-review/run-review/`
- `GET /api/autonomy-seed-review/resolutions/`
- `GET /api/autonomy-seed-review/recommendations/`
- `GET /api/autonomy-seed-review/summary/`
- `POST /api/autonomy-seed-review/acknowledge/<seed_id>/`
- `POST /api/autonomy-seed-review/accept/<seed_id>/`
- `POST /api/autonomy-seed-review/defer/<seed_id>/`
- `POST /api/autonomy-seed-review/reject/<seed_id>/`

## Scan agent filter hardening layer (new)

`research_agent` now includes a dedicated scan hardening pipeline exposed at `/api/scan-agent/*`:

- `POST /api/scan-agent/run-scan/`
- `GET /api/scan-agent/signals/`
- `GET /api/scan-agent/clusters/`
- `GET /api/scan-agent/recommendations/`
- `GET /api/scan-agent/summary/`

Service split (thin views, auditable services):
- `services/source_fetch.py`
- `services/dedup.py`
- `services/clustering.py`
- `services/scoring.py`
- `services/market_context.py`
- `services/recommendation.py`
- `services/run.py`

Scope remains local-first/manual-first/paper-only/read-only; no broker/exchange execution is introduced.


## Research Agent: market universe triage hardening

The backend now exposes `/api/research-agent/` endpoints for hardened universe triage:
- `POST run-universe-scan/`
- `GET candidates/`
- `GET triage-decisions/`
- `GET recommendations/`
- `GET universe-summary/`

Service split (lightweight + auditable):
- `services/universe_fetch.py`
- `services/filtering.py`
- `services/scoring.py`
- `services/narrative_linking.py`
- `services/recommendation.py`
- `services/run.py`

## Risk runtime hardening layer (new)

`apps.risk_agent` now includes an explicit runtime-governance boundary that consumes prediction runtime assessments and emits auditable paper-only decisions.

New entities:
- `RiskRuntimeRun`
- `RiskRuntimeCandidate`
- `RiskApprovalDecision`
- `RiskSizingPlan`
- `PositionWatchPlan`
- `RiskRuntimeRecommendation`

New endpoints:
- `POST /api/risk-agent/run-runtime-review/`
- `GET /api/risk-agent/runtime-candidates/`
- `GET /api/risk-agent/approval-decisions/`
- `GET /api/risk-agent/sizing-plans/`
- `GET /api/risk-agent/watch-plans/`
- `GET /api/risk-agent/runtime-recommendations/`
- `GET /api/risk-agent/runtime-summary/`

Service split:
- `services/candidate_building.py`
- `services/approval.py`
- `services/sizing_runtime.py`
- `services/watch_plan.py`
- `services/recommendation.py`
- `services/run.py`

Boundaries:
- conservative bounded/capped sizing (paper-only)
- recommendation-first handoff to execution simulator, portfolio governor context, and position-manager watch context
- manual-first apply, no live broker execution, no real money

## Postmortem learning loop hardening (new)

`apps.learning_memory` now includes a dedicated postmortem-learning loop runtime that extends (not replaces) postmortem board + learning memory:

New entities:
- `PostmortemLearningRun`
- `FailurePattern`
- `PostmortemLearningAdjustment`
- `LearningApplicationRecord`
- `LearningRecommendation`

Service split (thin views):
- `services/patterns.py`
- `services/adjustments_loop.py`
- `services/application.py`
- `services/recommendation.py`
- `services/run.py`

Primary endpoints:
- `POST /api/learning/run-postmortem-loop/`
- `GET /api/learning/failure-patterns/`
- `GET /api/learning/adjustments/`
- `GET /api/learning/application-records/`
- `GET /api/learning/recommendations/`
- `GET /api/learning/postmortem-loop-summary/`

Optional manual controls:
- `POST /api/learning/adjustments/<id>/activate/`
- `POST /api/learning/adjustments/<id>/expire/`
- `GET /api/learning/adjustments/<id>/`

Boundaries remain strict: recommendation-first + manual-first apply, conservative bounded adjustments, no opaque auto policy/risk changes, no model retraining.

## Opportunity cycle / signal fusion runtime hardening (new)

`apps.opportunity_supervisor` now also exposes a dedicated runtime review boundary for fused opportunity readiness.

Core entities:
- `OpportunityCycleRuntimeRun`
- `OpportunityFusionCandidate`
- `OpportunityFusionAssessment`
- `PaperOpportunityProposal`
- `OpportunityRecommendation`

Service split:
- `services/candidate_building.py`
- `services/fusion.py`
- `services/portfolio_context.py`
- `services/proposal_handoff.py`
- `services/recommendation.py`
- `services/run.py`

New API:
- `POST /api/opportunity-cycle/run-review/`
- `GET /api/opportunity-cycle/candidates/`
- `GET /api/opportunity-cycle/assessments/`
- `GET /api/opportunity-cycle/proposals/`
- `GET /api/opportunity-cycle/recommendations/`
- `GET /api/opportunity-cycle/summary/`

Boundary guarantees: recommendation-first, local-first, manual-first, paper-only.


## Quantitative evaluation runtime hardening (2026-03-30)

- Added an auditable ex-post runtime evaluation layer under `evaluation_lab` that links resolved outcomes with prediction, risk, opportunity-fusion, and paper proposal artifacts.
- Added calibration buckets, effectiveness metrics, drift flags, and explicit human recommendations (manual-first, no auto-tuning/no auto-retraining).
- Added API endpoints under `/api/evaluation/*` for runtime evaluation execution and board data retrieval.
- Strengthened `/evaluation` frontend with outcome-alignment, calibration, effectiveness, recommendations, and manual trigger UX.
- Scope remains local-first, single-user, paper/sandbox only; no real-money execution or silent policy/model mutation.


## Governed tuning board (manual quantitative improvement loop)

The platform now includes a dedicated `tuning_board` layer (`/api/tuning/*` + `/tuning`) that converts `evaluation_lab` metrics/drift findings into explicit, bounded, reviewable tuning proposals.

- consumes `EvaluationRuntimeRun`, `EffectivenessMetric`, `CalibrationBucket`, and `EvaluationRecommendation` evidence
- emits auditable `TuningReviewRun`, `TuningProposal`, `TuningImpactHypothesis`, `TuningRecommendation`, and optional `TuningProposalBundle` records
- preserves metric -> recommendation -> proposal traceability and scoped targeting (global/provider/category/horizon/model_mode)
- integrates conceptually with `trust_calibration`, `policy_tuning`, `experiments`, `champion_challenger`, and `promotion_committee` without deep auto-integration in this step
- keeps strict manual-first governance: **no auto-tuning, no silent threshold mutation, no auto-retraining, no live-money execution**

Primary endpoints:
- `POST /api/tuning/run-review/`
- `GET /api/tuning/proposals/`
- `GET /api/tuning/hypotheses/`
- `GET /api/tuning/recommendations/`
- `GET /api/tuning/summary/`
- `GET /api/tuning/bundles/` (optional grouping panel)

## Promotion manual adoption action layer (new)

`apps.promotion_committee` now includes a post-approval adoption sub-layer that is manual-first and paper-only.

Core entities:
- `PromotionAdoptionRun`
- `AdoptionActionCandidate`
- `ManualAdoptionAction`
- `AdoptionRollbackPlan`
- `AdoptionActionRecommendation`

Service split:
- `services/candidate_building.py`
- `services/target_resolution.py`
- `services/action_planning.py`
- `services/rollback.py`
- `services/recommendation.py`
- `services/run.py`

Behavior:
- consumes only `PromotionCase.APPROVED_FOR_MANUAL_ADOPTION`
- produces bounded manual actions with explicit snapshots and blockers
- prepares rollback plans for sensitive/risk-bearing paths
- optionally prepares rollout handoff actions in paper/demo mode
- records manual apply via explicit operator endpoint only

Boundaries preserved:
- no auto-apply
- no auto-rollout
- no live execution or real money paths

## Rollout preparation and manual rollback layer (promotion_committee)

`promotion_committee` now includes a dedicated rollout-prep runtime that reuses existing adoption artifacts rather than replacing them.

Services (`apps/promotion_committee/services/rollout_prep/`):
- `candidate_building.py`
- `rollout_planning.py`
- `checkpoints.py`
- `rollback_execution.py`
- `recommendation.py`
- `run.py`

Behavior:
- consumes `ManualAdoptionAction` (+ `AdoptionRollbackPlan` when available)
- classifies `DIRECT_APPLY_OK` / `ROLLOUT_RECOMMENDED` / `ROLLOUT_REQUIRED`
- prepares `ManualRolloutPlan` and `RolloutCheckpointPlan`
- prepares and records `ManualRollbackExecution`
- exposes manual rollback endpoint (`POST /api/promotion/rollback/<action_id>/`)
- maintains paper/demo-only bridge metadata toward `rollout_manager`

Explicitly out of scope:
- any auto-rollout / auto-switch
- live broker/exchange execution
- silent mutation paths

## Manual rollout execution + post-rollout safety loop (new)

`apps.promotion_committee` now adds a dedicated manual execution layer on top of rollout preparation.

### What it does
- consumes `ManualRolloutPlan` + `RolloutCheckpointPlan` prepared by rollout prep
- records manual rollout execution and stage progress
- records auditable real checkpoint outcomes (`PASSED` / `FAILED` / `WARNING` / `SKIPPED`)
- emits post-rollout safety state (`HEALTHY` / `CAUTION` / `REVIEW_REQUIRED` / `ROLLBACK_RECOMMENDED` / `REVERTED` / `INCOMPLETE`)
- emits conservative bounded recommendations for manual continue/pause/review/rollback/close

### Service split
- `services/rollout_execution/execution.py`
- `services/rollout_execution/checkpoint_outcomes.py`
- `services/rollout_execution/post_rollout_status.py`
- `services/rollout_execution/recommendation.py`
- `services/rollout_execution/run.py`

### Boundaries
- no auto-rollout
- no auto-rollback
- no live trading / real-money execution
- evaluation/risk/trust/policy contribute context signals only

## Post-rollout certification / stabilization gate (new)

`apps.certification_board` now includes a post-rollout stabilization layer that is separate from rollout execution:

- consumes `RolloutExecutionRecord`, `CheckpointOutcomeRecord`, and `PostRolloutStatus` from `promotion_committee`
- builds auditable entities:
  - `RolloutCertificationRun`
  - `CertificationCandidate`
  - `CertificationEvidencePack`
  - `CertificationDecision`
  - `CertificationRecommendation`
- keeps governance manual-first and paper-only (no auto-certification, no auto-promotion, no auto-rollback)

Service split:
- `services/candidate_building.py`
- `services/evidence_pack.py`
- `services/decision.py`
- `services/recommendation.py`
- `services/run.py`

API endpoints:
- `POST /api/certification/run-post-rollout-review/`
- `GET /api/certification/candidates/`
- `GET /api/certification/evidence-packs/`
- `GET /api/certification/decisions/`
- `GET /api/certification/recommendations/`
- `GET /api/certification/post-rollout-summary/`

Boundary clarification:
- rollout execution remains in `promotion_committee`.
- certification consumes rollout evidence and emits recommendations only.
- baseline confirmation stays explicit/manual; no active champion switch is applied automatically.

## Baseline confirmation layer (certification_board)

`apps.certification_board` now includes a post-certification baseline-adoption layer.

Services:
- `services/candidate_building.py`: builds baseline candidates from `CertificationDecision.CERTIFIED_FOR_PAPER_BASELINE`
- `services/binding_resolution.py`: resolves previous/proposed baseline references + champion/policy/trust/rollout mapping snapshots
- `services/confirmation.py`: creates `PaperBaselineConfirmation` and before/after binding snapshots; manual confirm endpoint only
- `services/rollback.py`: prepares rollback availability using previous baseline snapshot
- `services/recommendation.py`: emits conservative confirmation recommendations
- `services/run.py`: orchestrates `BaselineConfirmationRun`

Scope/constraints:
- certify != baseline switch
- no auto baseline mutation
- no auto champion switch
- explicit manual confirmation and rollback preparation only
- paper/sandbox governance only


## Paper baseline activation board

The certification domain now includes a **paper baseline activation board** that sits after `PaperBaselineConfirmation=CONFIRMED`. It creates manual activation candidates, resolves active-binding replacement targets, records before/after snapshots, updates an explicit active paper binding registry, and keeps rollback reversible and auditable. This layer is manual-first, paper-only, local-first, and does not auto-switch champion, auto-promote, or execute live trading.

## Baseline health watch in certification_board (new)

A post-activation health layer now runs inside `apps.certification_board` and reuses evaluation/risk/opportunity context instead of duplicating those runtimes.

Service split:
- `services/baseline_health/candidate_building.py`
- `services/baseline_health/signals.py`
- `services/baseline_health/health_status.py`
- `services/baseline_health/recommendation.py`
- `services/baseline_health/run.py`

Intent:
- active baseline != healthy forever
- classify health as `HEALTHY`, `UNDER_WATCH`, `DEGRADED`, `REVIEW_REQUIRED`, `ROLLBACK_REVIEW_RECOMMENDED`, `INSUFFICIENT_DATA`
- emit explicit recommendation-first follow-up (`KEEP_BASELINE_ACTIVE`, `REQUIRE_REEVALUATION`, `OPEN_TUNING_REVIEW`, `PREPARE_ROLLBACK_REVIEW`)

Out of scope: auto-retune, auto-deactivate, auto-promote, auto-switch champion, live trading.

## Baseline response board / degradation case registry (new)

`apps.certification_board` now adds a **baseline response** layer after baseline health watch.

Purpose:
- consume `BaselineHealthStatus`, `BaselineHealthSignal`, `BaselineHealthRecommendation`
- open auditable `BaselineResponseCase` records with manual-first statuses
- attach `ResponseEvidencePack` with confidence/severity/urgency
- attach `ResponseRoutingDecision` to `evaluation_lab`, `tuning_board`, `rollback_review`, `certification_board`, `promotion_committee`, or `monitoring_only`
- emit `BaselineResponseRecommendation` without auto-applying any tuning/rollback/deactivation

Run/service split:
- `services/baseline_response/candidate_building.py`
- `services/baseline_response/evidence_pack.py`
- `services/baseline_response/routing.py`
- `services/baseline_response/recommendation.py`
- `services/baseline_response/run.py`

API:
- `POST /api/certification/run-baseline-response-review/`
- `GET /api/certification/response-cases/`
- `GET /api/certification/response-evidence-packs/`
- `GET /api/certification/response-routing-decisions/`
- `GET /api/certification/response-recommendations/`
- `GET /api/certification/response-summary/`

Out of scope (unchanged): no auto-retune, no auto-rollback, no auto-deactivate baseline, no live/real-money execution.

## Baseline response actions & tracking (manual-first)

`certification_board` now includes a baseline response actions sublayer that executes **manual routing handoff records** and **downstream tracking** on top of existing baseline response outputs.

New API endpoints:
- `POST /api/certification/run-baseline-response-actions/`
- `GET /api/certification/response-action-candidates/`
- `GET /api/certification/response-routing-actions/`
- `GET /api/certification/response-tracking-records/`
- `GET /api/certification/response-action-recommendations/`
- `GET /api/certification/response-action-summary/`
- `POST /api/certification/route-response-case/<case_id>/`
- `POST /api/certification/update-response-tracking/<case_id>/`
- `POST /api/certification/close-response-case/<case_id>/`
- `GET /api/certification/response-routing-actions/<id>/`
- `GET /api/certification/response-tracking-records/<id>/`

Scope:
- consumes `BaselineResponseCase + ResponseRoutingDecision`
- creates auditable `ResponseRoutingAction` and `ResponseCaseTrackingRecord`
- keeps routing/apply explicitly manual (no auto-open of downstream boards)
- paper-only, local-first, single-user conservative flow

## Baseline downstream response lifecycle layer (new)

`apps.certification_board` now includes a formal downstream lifecycle loop on top of baseline response actions/tracking.

### New lifecycle entities
- `BaselineResponseLifecycleRun`
- `DownstreamAcknowledgement`
- `ResponseReviewStageRecord`
- `DownstreamLifecycleOutcome`
- `ResponseLifecycleRecommendation`

### API endpoints
- `POST /api/certification/run-baseline-response-lifecycle/`
- `GET /api/certification/downstream-acknowledgements/`
- `GET /api/certification/review-stage-records/`
- `GET /api/certification/downstream-lifecycle-outcomes/`
- `GET /api/certification/response-lifecycle-recommendations/`
- `GET /api/certification/response-lifecycle-summary/`
- `POST /api/certification/acknowledge-response-case/<case_id>/`
- `POST /api/certification/update-response-stage/<case_id>/`
- `POST /api/certification/record-downstream-outcome/<case_id>/`

### Design boundaries
- consumes existing `ResponseRoutingAction` + `ResponseCaseTrackingRecord`
- does not auto-open downstream board entities
- does not auto-resolve cases and does not auto-apply tuning/rollback
- remains local-first, manual-first, single-user, paper/sandbox only


### Baseline response resolution (Prompt 133 revised)
- Adds a formal manual-first layer after downstream lifecycle: resolution candidates, proposed case resolutions, downstream evidence references, and conservative closure recommendations.
- Keeps existing routing/tracking/lifecycle intact and does not auto-close cases. Final closure remains explicit via `POST /api/certification/resolve-response-case/<case_id>/`.
- New run/board endpoint: `POST /api/certification/run-baseline-response-resolution/` with list/summary endpoints for candidates, resolutions, references, and recommendations.
- Scope remains paper/sandbox only (no live trading, no auto-retune/rollback/deactivate/promote).

## Autonomous trader module (new)

Backend now includes `apps.autonomous_trader` as a paper-only orchestration layer for minimal-human-intervention cycles:

- services split by responsibility:
  - `services/candidate_intake.py`
  - `services/decisioning.py`
  - `services/execution.py`
  - `services/watch.py`
  - `services/outcomes.py`
  - `services/run.py`
- API:
  - `POST /api/autonomous-trader/run-cycle/`
  - `POST /api/autonomous-trader/run-watch-cycle/`
  - `GET /api/autonomous-trader/{cycles,candidates,decisions,executions,watch-records,outcomes,summary}/`

The module is local-first and paper-only; it does not implement real broker/exchange auth or live order routing.

## Autonomous outcome handoff closure (new)

`apps.autonomous_trader` now includes a formal post-trade handoff engine that keeps governance explicit and auditable.

New entities:
- `AutonomousOutcomeHandoffRun`
- `AutonomousPostmortemHandoff`
- `AutonomousLearningHandoff`
- `AutonomousOutcomeHandoffRecommendation`

Service split:
- `services/outcome_handoff/handoff_selection.py`
- `services/outcome_handoff/postmortem_handoff.py`
- `services/outcome_handoff/learning_handoff.py`
- `services/outcome_handoff/recommendation.py`
- `services/outcome_handoff/run.py`

Integration model:
- `autonomous_trader` decides *when* to hand off and records lineage/dedupe/audit status.
- `postmortem_demo` + `postmortem_agents` remain the authority for postmortem generation and board execution.
- `learning_memory` remains the authority for conservative learning capture.

Still not implemented (by design): real execution, real money, auto-retune, auto-promote, or black-box planner authority.

## Autonomous feedback reuse bridge (new)

`apps.autonomous_trader` now includes a dedicated feedback-reuse layer that consumes retrieval context from `memory_retrieval` and learning/postmortem traces to influence the **next paper cycle** conservatively.

Added entities:
- `AutonomousFeedbackReuseRun`
- `AutonomousFeedbackCandidateContext`
- `AutonomousFeedbackInfluenceRecord`
- `AutonomousFeedbackRecommendation`

Service split:
- `services/feedback_reuse/feedback_retrieval.py`
- `services/feedback_reuse/influence.py`
- `services/feedback_reuse/watch_feedback.py`
- `services/feedback_reuse/recommendation.py`
- `services/feedback_reuse/run.py`

Endpoints:
- `POST /api/autonomous-trader/run-feedback-reuse/`
- `GET /api/autonomous-trader/feedback-reuse-runs/`
- `GET /api/autonomous-trader/feedback-candidate-contexts/`
- `GET /api/autonomous-trader/feedback-influences/`
- `GET /api/autonomous-trader/feedback-recommendations/`
- `GET /api/autonomous-trader/feedback-summary/`

Boundary:
- bounded influence only (caution/confidence/watch/block-repeat)
- no override of risk/policy/safety authority
- paper-only and local-first unchanged

## Autonomous trader Kelly sizing bridge (new)

`apps.autonomous_trader` now includes a risk-first paper sizing bridge:

- `AutonomousSizingRun`, `AutonomousSizingContext`, `AutonomousSizingDecision`, `AutonomousSizingRecommendation`
- service split under `services/kelly_sizing/`:
  - `sizing_context.py`
  - `kelly.py`
  - `adjustment.py`
  - `recommendation.py`
  - `run.py`
- endpoints:
  - `POST /api/autonomous-trader/run-sizing/`
  - `GET /api/autonomous-trader/sizing-runs/`
  - `GET /api/autonomous-trader/sizing-contexts/`
  - `GET /api/autonomous-trader/sizing-decisions/`
  - `GET /api/autonomous-trader/sizing-recommendations/`
  - `GET /api/autonomous-trader/sizing-summary/`

Boundary remains unchanged: paper-only, no broker/exchange live execution, no auto-retune, no auto-promote.

<<<<<<< HEAD
## Scan-to-research intelligence handoff hardening (new)

`apps.research_agent` now includes an explicit consensus/divergence/handoff-priority layer for scan output quality hardening.

Models:
- `NarrativeConsensusRun`
- `NarrativeConsensusRecord`
- `NarrativeMarketDivergenceRecord`
- `ResearchHandoffPriority`
- `NarrativeConsensusRecommendation`

Service split:
- `services/intelligence_handoff/consensus.py`
- `services/intelligence_handoff/divergence.py`
- `services/intelligence_handoff/handoff_priority.py`
- `services/intelligence_handoff/recommendation.py`
- `services/intelligence_handoff/run.py`

Boundary guarantees:
- improves scan→research handoff quality only
- does not replace `research_agent` formal market triage authority
- remains local-first, single-user, paper-only, no live execution
=======

## Autonomous position watch bridge
- New autonomous-trader position-watch services implement conservative open-position management (candidate assessment, action decision, paper execution, recommendation, run summary).
- API: run-position-watch, position-watch-runs, position-watch-candidates, position-action-decisions, position-action-executions, position-watch-recommendations, position-watch-summary.
- Strictly paper-only and traceable; no auto-retune, no auto-promote, no live trading path.
>>>>>>> origin/main

## Research pursuit hardening layer (new)

`apps.research_agent` now adds a dedicated research→prediction bridge with auditable entities:

- `ResearchPursuitRun`
- `ResearchStructuralAssessment`
- `ResearchPursuitScore`
- `PredictionHandoffCandidate`
- `ResearchPursuitRecommendation`

Service split:
- `services/pursuit_scoring/structural_assessment.py`
- `services/pursuit_scoring/pursuit_score.py`
- `services/pursuit_scoring/prediction_handoff.py`
- `services/pursuit_scoring/recommendation.py`
- `services/pursuit_scoring/run.py`

New endpoints:
- `POST /api/research-agent/run-pursuit-review/`
- `GET /api/research-agent/pursuit-runs/`
- `GET /api/research-agent/structural-assessments/`
- `GET /api/research-agent/pursuit-scores/`
- `GET /api/research-agent/prediction-handoffs/`
- `GET /api/research-agent/pursuit-recommendations/`
- `GET /api/research-agent/pursuit-summary/`

Design boundary:
- recommendation-first, transparent scoring components
- no live broker/exchange execution
- no real money
- does not replace `prediction_agent`, `risk_agent`, policy, runtime, or safety authority

## Prediction intake + conviction review bridge (new)

`apps.prediction_agent` now adds a conservative, auditable layer between research and risk.

New entities:
- `PredictionIntakeRun`
- `PredictionIntakeCandidate`
- `PredictionConvictionReview`
- `RiskReadyPredictionHandoff`
- `PredictionIntakeRecommendation`

New endpoints:
- `POST /api/prediction/run-intake-review/`
- `GET /api/prediction/intake-runs/`
- `GET /api/prediction/intake-candidates/`
- `GET /api/prediction/conviction-reviews/`
- `GET /api/prediction/risk-handoffs/`
- `GET /api/prediction/intake-recommendations/`
- `GET /api/prediction/intake-summary/`

Services:
- `services/intake.py`
- `services/conviction.py`
- `services/uncertainty.py`
- `services/risk_handoff.py`
- `services/recommendation.py`
- `services/run.py`

Design boundaries remain strict: paper-only, no real execution, no risk-authority replacement.


## Risk intake hardening layer (new)

`apps.risk_agent` now includes a formal intake+approval bridge from `prediction_agent` handoffs to autonomous paper execution readiness:

- runtime intake source: `prediction_agent.RiskReadyPredictionHandoff`
- auditable runtime entities: intake candidate context on `RiskRuntimeCandidate`, approval review on `RiskApprovalDecision`, and `AutonomousExecutionReadiness`
- recommendation layer: `RiskIntakeRecommendation` (conservative, explainable, reason-code driven)
- service split:
  - `services/intake.py`
  - `services/approval.py`
  - `services/execution_readiness.py`
  - `services/recommendation.py`
  - `services/run.py`

Primary endpoints:
- `POST /api/risk-agent/run-intake-review/`
- `GET /api/risk-agent/intake-runs/`
- `GET /api/risk-agent/intake-candidates/`
- `GET /api/risk-agent/approval-reviews/`
- `GET /api/risk-agent/execution-readiness/`
- `GET /api/risk-agent/intake-recommendations/`
- `GET /api/risk-agent/intake-summary/`

Boundary guarantees remain strict: paper-only, recommendation-first, and no live routing or real-money execution.

## Autonomous execution intake bridge (new)

`apps.autonomous_trader` now exposes a readiness-driven execution-intake layer sourced from `apps.risk_agent.AutonomousExecutionReadiness`.

New endpoints:
- `POST /api/autonomous-trader/run-execution-intake/`
- `GET /api/autonomous-trader/execution-intake-runs/`
- `GET /api/autonomous-trader/execution-intake-candidates/`
- `GET /api/autonomous-trader/execution-decisions/`
- `GET /api/autonomous-trader/dispatch-records/`
- `GET /api/autonomous-trader/execution-intake-recommendations/`
- `GET /api/autonomous-trader/execution-intake-summary/`

Service split:
- `services/execution_intake/intake.py`
- `services/execution_intake/decision.py`
- `services/execution_intake/dispatch.py`
- `services/execution_intake/recommendation.py`
- `services/execution_intake/run.py`

This hardens risk→autonomous paper dispatch with explicit, auditable, policy-safe decisions and no live execution path.


## Autonomous Runtime Loop (Mission Control)
- Mission Control now includes an auditable autonomous runtime run model with cycle plans, executions, outcomes, and recommendations.
- The loop remains paper/sandbox only and does not perform live broker/exchange routing.
- Services are split into `cycle_plan`, `cycle_execution`, `cycle_outcome`, `recommendation`, and `run` under `apps/mission_control/services/autonomous_runtime/`.

## Mission control: session timing policy

Mission control now ships a dedicated session timing policy sublayer (`apps/mission_control/services/session_timing`) that:

- manages reusable `AutonomousScheduleProfile` cadence profiles,
- computes `AutonomousSessionTimingSnapshot` with explicit `next_due_at`, quiet-window, cooldown and pressure context,
- records `AutonomousTimingDecision` and `AutonomousTimingRecommendation` for auditable heartbeat behavior,
- emits `AutonomousStopConditionEvaluation` for conservative pause/stop governance.

This extends the existing local heartbeat runner and keeps all execution paper-only and guardrail-first.

## Mission control adaptive session profile control (new)

`apps.mission_control` ahora incluye una subcapa `services/session_profile_control/` para seleccionar y cambiar perfiles de sesión según contexto operativo real, sin duplicar timing policy ni heartbeat runner.

### Entidades
- `AutonomousProfileSelectionRun`
- `AutonomousSessionContextReview`
- `AutonomousProfileSwitchDecision`
- `AutonomousProfileSwitchRecord`
- `AutonomousProfileRecommendation`

### Servicios
- `context_review.py`: evalúa portfolio/runtime/safety/signal/loss/activity por sesión.
- `profile_switch.py`: decide keep/switch/manual/block con reglas transparentes y aplica switch conservador.
- `recommendation.py`: emite recomendaciones auditables con rationale/reason_codes/confidence/blockers.
- `run.py`: ejecuta batch review y publica resumen agregado.

### API
- `POST /api/mission-control/run-profile-selection-review/`
- `GET /api/mission-control/session-context-reviews/`
- `GET /api/mission-control/profile-switch-decisions/`
- `GET /api/mission-control/profile-switch-records/`
- `GET /api/mission-control/profile-recommendations/`
- `GET /api/mission-control/profile-selection-summary/`
- `POST /api/mission-control/apply-profile-switch/<decision_id>/` (manual opcional)

Esta capa alimenta mejor la timing policy; no reemplaza runtime/policy/safety/portfolio authorities.

## Mission control global session admission

Backend mission_control now exposes a global session admission control flow:

- `run-session-admission-review`
- `global-capacity-snapshots`
- `session-admission-reviews`
- `session-admission-decisions`
- `session-admission-recommendations`
- `session-admission-summary`

This layer is conservative and auditable, coordinates cross-session capacity, and consumes portfolio/runtime/safety/health/recovery signals without replacing those authorities.


## Portfolio governor global exposure coordination (new)

`apps.portfolio_governor` now includes a conservative paper-only exposure harmonizer:

- service split:
  - `services/clusters.py`
  - `services/conflict_review.py`
  - `services/decision.py`
  - `services/recommendation.py`
  - `services/run.py`
- auditable entities:
  - `PortfolioExposureCoordinationRun`
  - `PortfolioExposureClusterSnapshot`
  - `SessionExposureContribution`
  - `PortfolioExposureConflictReview`
  - `PortfolioExposureDecision`
  - `PortfolioExposureRecommendation`
- API:
  - `POST /api/portfolio-governor/run-exposure-coordination-review/`
  - `GET /api/portfolio-governor/exposure-coordination-runs/`
  - `GET /api/portfolio-governor/exposure-cluster-snapshots/`
  - `GET /api/portfolio-governor/session-exposure-contributions/`
  - `GET /api/portfolio-governor/exposure-conflict-reviews/`
  - `GET /api/portfolio-governor/exposure-decisions/`
  - `GET /api/portfolio-governor/exposure-recommendations/`
  - `GET /api/portfolio-governor/exposure-coordination-summary/`

Boundary guarantees remain strict: local-first, single-user, paper-only, no broker/exchange live routing, no real money, and no LLM as final throttling authority.

## Portfolio governor exposure apply & enforcement (new)

`apps.portfolio_governor` now extends exposure coordination with a conservative **apply bridge**:

- service split:
  - `services/apply_targets.py`
  - `services/apply_decision.py`
  - `services/apply_record.py`
  - `services/recommendation.py`
  - `services/run.py`
- new API:
  - `POST /api/portfolio-governor/apply-exposure-decision/<decision_id>/`
  - `POST /api/portfolio-governor/run-exposure-apply-review/`
  - `GET /api/portfolio-governor/exposure-apply-runs/`
  - `GET /api/portfolio-governor/exposure-apply-targets/`
  - `GET /api/portfolio-governor/exposure-apply-decisions/`
  - `GET /api/portfolio-governor/exposure-apply-records/`
  - `GET /api/portfolio-governor/exposure-apply-recommendations/`
  - `GET /api/portfolio-governor/exposure-apply-summary/`

Conservative enforcement scope: admission throttling, pending dispatch defer, runtime session park/pause, and explicit manual-review fallback for ambiguous decisions.

Hard limits remain unchanged: paper-only, local-first, no real broker/exchange routing, no real money, no aggressive position closures.

## Runtime governor global operating mode layer (new)

`apps.runtime_governor` now includes a conservative, auditable global posture/mode control layer:

- models:
  - `GlobalRuntimePostureRun`
  - `GlobalRuntimePostureSnapshot`
  - `GlobalOperatingModeDecision`
  - `GlobalOperatingModeSwitchRecord`
  - `GlobalOperatingModeRecommendation`
- services:
  - `services/operating_mode/posture.py`
  - `services/operating_mode/mode_switch.py`
  - `services/operating_mode/recommendation.py`
  - `services/operating_mode/run.py`
- integration:
  - influences runtime capability surface through explicit `global_operating_mode` constraints
  - emits downstream influence hints for cadence/admission/exposure/heartbeat behavior

Strict boundaries remain unchanged: local-first, paper/sandbox only, no real-money execution, and no replacement of mission-control/portfolio/safety/risk authorities.

## Global mode enforcement bridge
- Added mode-enforcement services (`rules`, `module_impacts`, `enforcement`, `recommendation`, `run`) under `runtime_governor`.
- New endpoints expose mode enforcement runs, impacts, decisions, recommendations, and summary.
- This layer propagates global operating mode into conservative downstream runtime restrictions without replacing timing/admission/exposure/safety authorities.
