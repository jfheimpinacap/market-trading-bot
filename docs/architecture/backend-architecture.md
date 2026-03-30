# Backend architecture

## Overview
The backend is a local-first Django service inside the monorepo. Its current responsibility is to provide a clean, maintainable API foundation plus a realistic local prediction-market catalog for backend and frontend development.

## Main layers
- `config/`: global project wiring such as settings, API aggregation, root URLs, ASGI/WSGI, and Celery.
- `apps/`: Django apps grouped by bounded responsibility.
- `apps/common/`: reusable technical primitives shared across future domain apps.
- `apps/*/urls.py`: per-app route registration.
- `apps/*/views.py` and `serializers.py`: DRF endpoint and payload boundaries.
- `apps/*/management/commands/`: reusable Django management commands, including local seed and simulation workflows.

## Precedent-aware decision support layer (new)

- `apps.memory_retrieval` now includes an explicit integration sublayer:
  - `services/assist.py`: query builders + standardized assist entrypoint
  - `services/influence.py`: influence summary, conservative mode suggestion, and audit persistence
- New model: `AgentPrecedentUse` (agent, source object, retrieval run, influence mode, metadata).
- Integrated consumers:
  - `research_agent.services.precedent_enrichment`
  - `prediction_agent.services.precedent_enrichment`
  - `risk_agent.services.precedent_enrichment`
  - `signals.services.precedent_enrichment`
  - `postmortem_agents.services.precedent_enrichment`
- Architectural rule: precedent memory augments context/rationale and may apply bounded caution, but cannot replace numeric risk/policy/safety guardrails.

## Current backend app roles
- `apps.common`: abstract timestamped models and shared technical helpers.
- `apps.health`: lightweight environment-oriented health endpoint.
- `apps.markets`: provider-agnostic prediction-market catalog with providers, events, markets, historical snapshots, rules, demo seed data, local simulation engine, admin tooling, and read-only endpoints for local UI work.
- `apps.paper_trading`: demo-only portfolio domain with virtual cash, positions, trades, portfolio snapshots, execution services, valuation services, admin tooling, and simple DRF endpoints.
- `apps.risk_demo`: demo-only pre-trade assessment domain that persists trade guard verdicts and keeps heuristic evaluation logic out of views.
- `apps.signals`: demo-only signals + signal-fusion domain with mock agents, legacy heuristic signals, fusion runs, opportunity board outputs, and proposal gating endpoints.
- `apps.postmortem_demo`: demo-only trade review domain that evaluates executed paper trades after the fact and exposes read-only review endpoints.
- `apps.agents`: reserved for later agent orchestration work.
- `apps.audit`: reserved for later audit and post-mortem persistence.
- `apps.policy_engine`: demo-only governance boundary that converts trade proposals into explicit approval outcomes.
- `apps.experiment_lab`: profile-driven experiment orchestration layer that reuses replay/evaluation services and produces auditable run comparisons.
- `apps.research_agent`: scan/research boundary for RSS + Reddit + optional X/Twitter adapter ingestion, local LLM structured analysis, social-signal normalization, heuristic market linking, and conservative mixed-source candidate fusion.
- `apps.position_manager`: post-entry holding governance boundary that consumes risk watch + prediction/research drift context to produce auditable HOLD/REDUCE/CLOSE/REVIEW decisions and explicit paper-only exit plans.
- `apps.policy_rollout`: post-change governance boundary that evaluates applied policy tuning impact against baseline metrics and emits recommendation-first keep/monitor/rollback guidance with manual rollback support.
- `apps.autonomy_advisory`: insight-to-artifact governance boundary that consumes reviewed autonomy insights, emits auditable advisory notes/stubs, and tracks dedup/manual blockers/run summaries.

## Autonomy advisory architecture (new)

`apps.autonomy_advisory` is intentionally adjacent to `apps.autonomy_insights`:

- `autonomy_insights` continues to synthesize lessons/patterns and produce insight recommendations.
- `autonomy_advisory` consumes those reviewed insights and emits formal advisory artifacts.

Service split:
- `services/candidates.py`: reviewed-readiness and candidate projection
- `services/dedup.py`: emitted-artifact duplicate checks
- `services/recommendation.py`: recommendation-first advisory suggestions
- `services/emission.py`: artifact creation and optional memory note persistence
- `services/control.py`: manual emit action per insight
- `services/run.py`: auditable run-level consolidation and summary counters

Boundary guarantees:
- no auto-apply mutations in roadmap/scenario/program/manager
- no opaque planner/ML authority
- local-first, single-user, paper/sandbox constraints preserved

## Policy rollout architecture (new)

`apps.policy_rollout` adds a focused post-change loop without duplicating `policy_tuning` lifecycle responsibilities.

Core entities:
- `PolicyRolloutRun`
- `PolicyBaselineSnapshot`
- `PolicyPostChangeSnapshot`
- `PolicyRolloutRecommendation`

Service split:
- `services/baseline.py`: start rollout run + baseline capture
- `services/observation.py`: post-change snapshot capture
- `services/comparison.py`: before/after metric delta computation
- `services/recommendation.py`: recommendation-first decisioning
- `services/rollback.py`: explicit manual rollback application

Integration points:
- `policy_tuning`: binds run to `PolicyTuningCandidate` + `PolicyTuningApplicationLog`
- `trust_calibration`: reuses metric semantics from trust calibration snapshot logic
- `automation_policy`: applies rollback restoration on policy rule trust tier/conditions
- `approval_center`: optional rollback-gate approval request creation
- `incident_commander` + `trace_explorer`: incident linkage and trace root metadata for root-cause drilldown

Boundaries:
- no auto-rollback without human confirmation
- no real-money or real-execution path changes
- no opaque planner behavior

## Market domain shape
The current `apps.markets` app is intentionally provider-agnostic.

Core relationships:
- `Provider` is the root source entity.
- `Event` groups related markets from a provider.
- `Market` represents the tradeable or analyzable market definition.
- `MarketSnapshot` stores time-series observations for a market.
- `MarketRule` stores fuller rule and resolution text separately from the market summary row.

This gives the backend a clean relational base before adding provider sync, signals, or paper trading layers.

## Paper trading domain shape
The `apps.paper_trading` app builds directly on `apps.markets` and intentionally stays local-first.

Core relationships:
- `PaperAccount` represents a virtual account with cash, equity, and PnL state.
- `PaperPosition` tracks current exposure for one account, one market, and one side (`YES` or `NO`).
- `PaperTrade` records each immediate paper execution and links back to the position when relevant.
- `PaperPortfolioSnapshot` stores account-level history for future charts and timeline views.

Service split:
- `services/execution.py`: execute immediate demo trades and mutate account/position state
- `services/valuation.py`: resolve current mark prices, validate market tradability, and recalculate mark-to-market values
- `services/portfolio.py`: ensure the demo account exists, assemble summary payloads, and persist snapshots

This keeps trade logic out of views and avoids overloading model methods while staying simple enough for the current single-demo-account stage.

## Risk demo domain shape
The `apps.risk_demo` app now sits between `apps.paper_trading`, `apps.markets`, and `apps.signals` as a local-first guardrail layer.

Core relationships:
- `TradeRiskAssessment` stores one persisted evaluation of a proposed trade.
- Each assessment links to one `Market` and optionally the active `PaperAccount`.
- Assessments snapshot the market prices and probability used at evaluation time so the frontend can explain the verdict later.

Service split:
- `services/assessment.py`: deterministic heuristics for tradability, estimated cost, concentration, liquidity, activity, and signal alignment
- `serializers.py`: request/response boundaries for pre-trade evaluation and recent assessments
- `views.py`: thin API surface for `POST /api/risk/assess-trade/` and recent assessment browsing

This is intentionally a mock trade guard, not a real risk engine or execution policy layer.

## Policy engine domain shape
The `apps.policy_engine` app now sits after `apps.risk_demo` and before paper execution as the operational governance boundary.

Core relationships:
- `ApprovalDecision` stores one persisted policy result for one proposed trade.
- Each decision links back to a `Market`, the active `PaperAccount`, and optionally a `TradeRiskAssessment` plus the latest relevant `MarketSignal`.
- Decisions also snapshot matched rules, recommendation text, severity, and confidence so the frontend or admin can explain why a proposal was auto-approved, escalated, or blocked.

Service split:
- `services/evaluation.py`: build the combined market/account/risk/signal context, evaluate deterministic rules, and persist the decision
- `services/rules.py`: tiny explicit rule-match primitives used by the evaluator
- `serializers.py` and `views.py`: thin DRF boundary for evaluate/list/summary endpoints

Current architectural intent:
- reuse `risk_demo` output instead of duplicating analytical logic
- add governance rules such as market operability, cash sizing, exposure concentration, and automation thresholds
- keep all approval outcomes local-first, readable, and auditable
- prepare the system for future approval queues without implementing them yet

## Signals domain shape
The new `apps.signals` app intentionally sits between `apps.markets` and future automation work.

Core relationships:
- `MockAgent` represents a demo analysis role such as scan, prediction, research, or risk.
- `MarketSignal` attaches an explainable demo signal to one `Market` and optionally one `MockAgent`.
- `SignalRun` records each local generation pass so later system pages or admin tooling can inspect run history.

Current heuristics:
- compare current market probability against a simple baseline from recent snapshots
- detect fast local moves and extreme probabilities
- reduce actionability when spread is wide, activity is thin, or the market is paused/terminal
- keep score and confidence deterministic so local behavior is reproducible

This is intentionally not a real prediction engine, risk engine, or autonomous agent system. It is a local-first demo layer that prepares stable boundaries for later evolution.


## Post-mortem demo domain shape
The `apps.postmortem_demo` app sits after execution and reuses existing paper trading, markets, signals, and risk-demo context without introducing a complex analytics engine.

Core relationships:
- `TradeReview` stores one persisted review for one `PaperTrade`.
- Each review also links directly to the related `PaperAccount` and `Market` for simpler API consumption and admin filtering.
- Reviews optionally capture the latest relevant signal context and risk verdict at trade time.

Service split:
- `services/review.py`: deterministic post-trade heuristics, outcome classification, summary/rationale generation, and persistence
- `management/commands/generate_trade_reviews.py`: thin CLI boundary for local generation or refresh
- `serializers.py` and `views.py`: read-only DRF boundary for list, detail, and summary responses

This remains intentionally mock and heuristic. It does not attempt ML, statistical attribution, or real-world causal analysis.

## Local demo-data strategy
The current stage is designed to make the system feel alive locally without real external integrations.

Key choices:
- use a real management command, `python manage.py seed_markets_demo`
- keep the seed deterministic and reasonably idempotent via `update_or_create`
- populate multiple categories and market lifecycle states
- keep providers as plain catalog sources, not adapter integrations
- expose enough read-only data for list views, detail views, and small dashboard summaries

This allows admin and frontend work to proceed before ingestion jobs exist.

## Local simulation strategy
A small simulation layer now complements the static seed data.

### Package layout
- `apps/markets/simulation/utils.py`: reusable math and normalization helpers
- `apps/markets/simulation/rules.py`: eligibility, bounded drift, and conservative state-transition rules
- `apps/markets/simulation/engine.py`: tick execution, market mutation, and snapshot creation
- `apps/markets/management/commands/simulate_markets_tick.py`: single-run orchestration for local development
- `apps/markets/management/commands/simulate_markets_loop.py`: optional repeating loop for local live-like behavior

### Architectural intent
The simulation layer is deliberately small and service-oriented:
- management commands stay thin and mostly handle CLI I/O
- simulation rules are explicit and easy to tune later
- the existing market models remain the source of truth
- no new API endpoints are required
- the frontend simply reuses the existing read-only endpoints and refreshes them

### Current simulation rules
- only demo markets are eligible
- terminal markets such as `resolved`, `cancelled`, and `archived` are skipped
- open markets move more than paused or closed markets
- category-specific volatility is intentionally light and readable
- time pressure increases movement slightly as a market approaches resolution
- status transitions are conservative and limited to `open`, `paused`, `closed`, and `resolved`
- each useful tick creates a fresh `MarketSnapshot` aligned with the updated market fields


## Real provider read-only ingestion layer

A provider-agnostic real-data ingestion path now exists for **read-only market data**:

- `libs/provider-core`: shared interface (`ReadOnlyProviderClient`) and normalized record shape.
- `libs/provider-kalshi`: Kalshi public market-data adapter.
- `libs/provider-polymarket`: Polymarket Gamma public market-data adapter.
- `apps.markets.services.real_data_ingestion`: maps normalized records to `Provider/Event/Market/MarketSnapshot`.
- `apps.markets.management.commands.ingest_kalshi_markets` and `ingest_polymarket_markets`: manual pull commands.

Data source separation is explicit via `source_type` on `Event` and `Market`:
- `demo`
- `real_read_only`

This keeps demo trading workflows isolated while enabling real-market discovery and persistence.

Out of scope remains unchanged: no trading auth, no order execution, no real portfolio, no auto-sync workers.


## Paper trading on real-market data architecture

The paper-trading stack now treats **market-data source** and **execution mode** as independent concerns:

- `Market.source_type`: `demo` vs `real_read_only`
- execution mode for this stage: `paper_demo_only`

A shared pricing/tradability layer in `apps.paper_trading.services.market_pricing` provides:
- centralized yes/no price resolution with probability fallback
- explicit paper-tradability checks for market status/activity/pricing completeness
- clear rejection messages for non-operable real markets

Reuse across layers:
- paper execution + valuation reuse the same price resolution
- risk demo and policy engine consume the same tradability/pricing constraints
- proposal engine uses the same price source and avoids synthetic fallback pricing

This preserves auditability and avoids scattered conditional logic while keeping all execution fictional/local-first.

## API conventions
- All endpoints live under `/api/`.
- `config/api.py` is the single place where app endpoints are mounted.
- Each app owns its own URL patterns and request/response serializers.
- The health endpoint is kept intentionally lightweight and configuration-oriented.
- Market endpoints are read-only and currently optimized for local catalog browsing.
- Paper trading endpoints are intentionally simple and assume a single active demo account by default.
- Market list and detail serializers intentionally differ so that lists stay lightweight while detail views include rules and recent snapshots.
- Signals endpoints are read-only and intentionally simple, with manual filtering and ordering instead of heavier query infrastructure.
- Post-mortem endpoints are also read-only and intentionally lightweight, with only list/detail/summary plus basic filters and ordering.

## Execution-aware replay/evaluation/readiness architecture

A lightweight execution realism bridge now connects replay, evaluation, experiments, and readiness without changing the local-first paper boundary.

- `apps.replay_lab.services.execution_replay`:
  - maps proposal intent to simulator paper orders
  - runs order lifecycle attempts
  - summarizes fill/no-fill/partial/slippage/drag metrics
- `apps.evaluation_lab.services.execution_metrics`:
  - builds execution-aware ratios from `PaperExecutionAttempt`
  - injects execution-adjusted snapshot metadata into evaluation runs
- `apps.experiment_lab.services.execution_comparison`:
  - computes naive-vs-aware deltas for experiment comparisons
- `apps.readiness_lab.services.execution_readiness`:
  - aggregates execution-aware replay evidence
  - applies bounded readiness penalty when fill realism is weak

Design intent:
- keep decision quality and execution quality distinguishable
- preserve naive metrics for before/after comparison
- avoid new heavyweight apps and avoid view-layer business logic
- remain paper/demo only (no real routing, no real money)

## Admin strategy
The admin is being treated as a practical local operations console.

Current goals:
- inspect seeded catalog data quickly
- understand provider/event/market relationships at a glance
- review recent market snapshots without leaving the market detail page
- verify simulation activity from market metadata and latest snapshots
- inspect the demo paper account, positions, trades, and portfolio snapshots after local executions
- keep editing surfaces simple and maintainable instead of building custom back-office tooling

## Settings strategy
- `base.py` contains shared defaults.
- `local.py` keeps local development behavior simple.
- `lite.py` provides a portable local profile (`config.settings.lite`) using SQLite and optional Redis.
- `test.py` uses SQLite and eager Celery execution for lightweight test runs.
- Environment variables control PostgreSQL, Redis, hosts, CORS, and runtime profile.

## Celery strategy
- Celery is initialized in `config/celery.py`.
- Redis is the default broker/result backend via environment variables.
- Lite mode switches to eager/in-memory execution so local notebooks can run without Redis.
- Apps can add `tasks.py` incrementally; Celery autodiscovery is already enabled.
- Real ingestion or sync tasks are intentionally deferred to a later stage.

## Growth guidelines
- Add business models only when a domain scope is ready.
- Keep shared code in `apps/common` small and reusable.
- Prefer explicit app boundaries instead of deeply nested internal frameworks.
- Avoid cross-app coupling until domain workflows become concrete.
- Extend the paper trading domain next with richer portfolio history, better summaries, optional auth, and frontend trading workflows while keeping the current demo-only execution model.

## Automation demo boundary

A new `apps/automation_demo/` boundary now coordinates explicit demo actions across the existing market simulation, signal generation, paper portfolio valuation, and post-mortem review services. The orchestration stays synchronous and local-first: each API request creates a `DemoAutomationRun`, executes one action or a sequential demo cycle, stores step-level details in JSON, and returns a readable result to the UI. This keeps automation guided and explainable without introducing Celery orchestration, schedulers, or autonomous trading behavior.

- semi_auto_demo app orchestrates evaluate-only and guarded paper auto-execution while keeping policy engine as the approval authority.


### Safety guard boundary

A dedicated `safety_guard` app now sits above risk+policy to enforce system-level operational limits (cooldown, hard stop, kill switch, exposure/session guardrails). It integrates with `continuous_demo` and `semi_auto_demo` via service calls and emits auditable `SafetyEvent` records.

## Learning memory layer (heuristic demo)

Nueva capa backend `apps.learning_memory`:
- Ingesta: reviews + evaluation metrics + safety events
- Persistencia: `LearningMemoryEntry` y `LearningAdjustment`
- Servicios: `ingest.py`, `adjustments.py`, `heuristics.py`
- Integración: proposal/risk reciben solo nudges conservadores y auditable metadata
- Rebuild explícito: command + endpoint

## Prediction model governance layer

`apps.prediction_training` now includes a conservative model-governance boundary:

- `ModelEvaluationProfile`: metric weights + minimum thresholds.
- `ModelComparisonRun` + `ModelComparisonResult`: auditable predictor comparison history.
- services split:
  - `services/comparison.py`: executes offline/scope-aware comparison.
  - `services/evaluation.py`: profile registry/defaults.
  - `services/recommendation.py`: recommendation decisioning.
  - `services/governance.py`: active-summary aggregation.

Runtime boundary remains explicit:
- `prediction_agent` keeps runtime scoring.
- no automatic model activation occurs.
- operator must call activate endpoint manually.


## Controlled learning loop integration

A conservative integration path now connects `learning_memory` with automation layers:

- `LearningRebuildRun` provides explicit rebuild audit trails.
- `learning_memory.services.integration.run_learning_rebuild` centralizes ingest + rebuild + run logging.
- `automation_demo` exposes explicit rebuild actions (manual and full-learning-cycle composite).
- `continuous_demo` can optionally trigger rebuild using conservative cadence settings.

Design intent stays deterministic and auditable: no ML/LLM, no real execution, no opaque self-tuning.

## Real data sync boundary (`apps.real_data_sync`)

A dedicated backend app now owns **provider sync orchestration** for real read-only data while reusing existing provider adapters and normalization.

Responsibilities:
- create and persist `ProviderSyncRun` records for every refresh
- invoke existing ingestion service (`apps.markets.services.real_data_ingestion`) without duplicating provider logic
- expose provider sync status and stale/degraded signals for technical/system surfaces
- provide manual execution boundaries (API + management command)

Why this boundary:
- keeps provider client logic centralized in adapter libs
- keeps sync/audit logic explicit and queryable
- prepares safe foundations for future scheduling without introducing distributed complexity now

Out of scope remains unchanged:
- real execution/auth
- websockets/streaming
- complex distributed sync orchestration


### Real-market operation scope layer
A dedicated backend app `real_market_ops` extends semi-auto/continuous orchestration with a conservative real-market-only scope:
- central eligibility service (provider health + freshness + paper tradability + pricing/liquidity/volume/category checks)
- explicit run persistence (`RealMarketOperationRun`)
- scope config persistence (`RealScopeConfig`)
- API control surface for evaluate/run/status/history.

Integration notes:
- reuses proposal, risk, policy, safety, and paper execution components
- continuous demo can opt-in via `market_scope=real_only` + `use_real_market_scope=true`
- still hard-limited to read-only real data + paper/demo execution only.

## Allocation engine boundary (demo)

Nuevo boundary backend: `apps/allocation_engine/`.

Orden funcional:
`proposal -> risk -> policy -> safety -> allocation -> paper execution`

Principios:
- no duplica lógica de policy/safety
- solo prioriza y reparte capital dentro de propuestas ya permitidas
- produce trazabilidad completa de por qué una propuesta se selecciona, reduce, salta o rechaza

Servicios:
- `services/ranking.py`: ranking heurístico auditable
- `services/portfolio_context.py`: cash/exposición actual
- `services/allocation.py`: aplicación de límites y decisión final

Persistencia:
- `AllocationRun`: snapshot de corrida
- `AllocationDecision`: decisión por propuesta (SELECTED/REDUCED/SKIPPED/REJECTED)

API:
- `POST /api/allocation/evaluate/`
- `POST /api/allocation/run/`
- `GET /api/allocation/runs/`
- `GET /api/allocation/runs/<id>/`
- `GET /api/allocation/summary/`

## Operator queue boundary

A dedicated `operator_queue` app now centralizes manual intervention into a single backend boundary.

Architecture role:
- consume escalations and approval-required cases (currently from `semi_auto_demo` and `real_market_ops` via `PendingApproval` integration)
- expose a unified API for list/detail/summary and manual decisions
- persist full decision audit logs (`OperatorDecisionLog`)
- keep decision logic in services (`queue.py`, `escalation.py`, `decisions.py`) instead of views

Operational constraints remain unchanged:
- paper/demo execution only
- no real exchange execution/auth
- no multi-user workflow engine
- no external push systems/websockets

## Replay architecture boundary (`apps.replay_lab`)

`replay_lab` is a thin orchestration layer for historical replay/backtest-like demo runs.

Core persisted entities:
- `ReplayRun`: run config/scope, aggregate counters, pnl/equity summary, status lifecycle
- `ReplayStep`: per-timestamp step counters and audit notes

Service split:
- `services/timeline.py`: snapshot query + chronological timeline construction
- `services/engine.py`: replay loop, proposal/policy/allocation/safety integration, step persistence
- `services/execution.py`: isolated replay account lifecycle and temporary activation context
- `services/metrics.py`: summary payloads for API/UI

Operational design:
- no live provider calls in replay execution path
- no real execution path
- replay account isolation prevents state contamination of operational paper account


## Experiment lab architecture
`apps.experiment_lab` is an orchestration and comparison boundary, not a duplicate execution engine.

- Reuses `apps.replay_lab.services.run_replay` for historical replay execution.
- Reuses `apps.evaluation_lab.services.build_run_for_continuous_session` or existing evaluation runs for live-paper metrics.
- Normalizes replay/evaluation outputs into a shared metric dictionary in `ExperimentRun.normalized_metrics`.
- Compares two experiment runs via `services/comparison.py` to produce metric deltas and interpretation hints.

This keeps experiments auditable and maintainable while preserving existing engine ownership:
- replay remains historical source of truth
- evaluation remains live-paper source of truth
- experiment_lab only orchestrates and compares

## Readiness/promotion gate architecture (new)

A dedicated `apps.readiness_lab` domain now formalizes go-live readiness decisions for paper/demo workflows.

Design goals:
- keep decision logic out of views
- make gates explicit and auditable
- persist each readiness assessment run
- reuse existing evidence from evaluation/replay/experiments/safety/operator queue

Core models:
- `ReadinessProfile`: threshold definition of what “ready” means
- `ReadinessAssessmentRun`: persisted decision + counts + detailed gate evidence

Service split:
- `assessment.py`: aggregates metrics and computes final `READY`/`CAUTION`/`NOT_READY`
- `gates.py`: standard comparator-based gate evaluation
- `recommendations.py`: deterministic remediation suggestions

This layer is intentionally advisory/governance-only: no automatic promotion and no real execution path.

## Runtime governance architecture (new)

A dedicated backend boundary `apps.runtime_governor` now governs operational autonomy modes.

Core concepts:
- `RuntimeModeProfile`: explicit capability matrix per mode (`OBSERVE_ONLY`, `PAPER_ASSIST`, `PAPER_SEMI_AUTO`, `PAPER_AUTO`)
- `RuntimeModeState`: singleton-like persisted effective mode + status (`ACTIVE`, `DEGRADED`, `PAUSED`, `STOPPED`)
- `RuntimeTransitionLog`: auditable transition records with source and rationale

Service split:
- `services/state.py`: state/profile bootstrap and retrieval
- `services/capabilities.py`: effective capability resolution with safety overrides
- `services/governance.py`: transition validation, readiness/safety constraints, and reconciliation
- `services/transitions.py`: transition logging

Cross-app integration:
- `semi_auto_demo`, `continuous_demo`, and `real_market_ops` now call runtime reconciliation/capabilities before execution.
- runtime governor consumes readiness/safety state; it does not duplicate those domains.

Boundary remains strict:
- no real-money mode
- no exchange execution path
- no automatic promotion to real operations

## Operator alerts architecture boundary

`apps/operator_alerts` introduces an internal incident-center layer for exception-driven oversight.

### Responsibilities
- persist actionable `OperatorAlert` records (severity, status, source, dedupe)
- aggregate signals from queue, safety, runtime governance, real sync, readiness, and continuous demo
- expose acknowledge/resolve operator state transitions
- generate persisted `OperatorDigest` windows

### Design choices
- dedupe is key-based and intentionally simple/auditable
- aggregation is pull-based (`rebuild`) to avoid hidden side effects in unrelated views
- no external transport integrations in this phase (email/SMS/chat/push)
- no autonomous real execution path

## Notification delivery architecture (new)

Se añade un bounded context explícito `apps.notification_center` encima de `operator_alerts`:

- `operator_alerts`: detecta, deduplica y persiste incidentes/digests (source of truth).
- `notification_center`: evalúa reglas de salida, selecciona canales y registra cada intento de entrega.

### Modelo
- `NotificationChannel`
- `NotificationRule`
- `NotificationDelivery`

### Pipeline
1. recibir `OperatorAlert` o `OperatorDigest`
2. evaluar reglas habilitadas por modo (`immediate` o `digest`)
3. validar umbral de severidad + `match_criteria`
4. resolver canales (fallback `ui_only`)
5. aplicar dedupe/cooldown simple
6. despachar y registrar resultado

### Scope guardrails
- local-first, paper/demo only
- sin colas distribuidas complejas
- sin campañas ni multiusuario enterprise
- sin ejecución real

## Notification automation architecture (new)

`apps.notification_center` now separates three concerns with small services:

- `services/automation.py`: event-driven immediate dispatch decisioning for open alerts
- `services/scheduler.py`: controlled digest cycle (`cycle_window`) generation and delivery
- `services/escalation.py`: persistence-based escalation run with auditable reason records

Key boundaries:
- `operator_alerts` stays source of truth for incidents.
- notification automation only reacts, routes, dispatches, suppresses, and records.
- existing rule matching + dedupe + cooldown continue to be enforced.
- no Celery/distributed scheduler requirement in this phase.

## Local LLM integration architecture (`apps.llm_local`)

A dedicated backend boundary now exists for local-first LLM usage through Ollama.

Layer split:
1. **Client layer**
   - `clients/ollama.py`: local chat + structured JSON output calls
   - `clients/embeddings.py`: local embedding vectors
2. **Prompt + schema layer**
   - `prompts/proposal.py`, `prompts/postmortem.py`, `prompts/learning.py`
   - `schemas.py`: explicit validation for JSON responses
3. **Task service layer**
   - `services/proposal_text.py`
   - `services/postmortem_text.py`
   - `services/learning_text.py`
   - `services/embeddings.py`
   - `services/status.py`
4. **API boundary**
   - `GET /api/llm/status/`
   - `POST /api/llm/proposal-thesis/`
   - `POST /api/llm/postmortem-summary/`
   - `POST /api/llm/learning-note/`
   - `POST /api/llm/embed/`

Current role is intentionally narrow and auditable: narrative enrichment and structured text outputs. It does not replace risk/policy/safety decisioning and does not execute trades.

## Research narrative scan architecture (MVP)

`apps.research_agent` adds the first narrative ingestion/research boundary while preserving existing governance:

Flow:
1. ingest RSS sources (`NarrativeSource` -> `NarrativeItem`)
2. run structured narrative analysis (`NarrativeAnalysis`)
3. link to active markets (`MarketNarrativeLink`)
4. compute shortlist candidates (`ResearchCandidate`)
5. persist run audit (`ResearchScanRun`)

Design constraints:
- local-first and paper/demo only
- LLM provides narrative enrichment only
- risk/policy/safety stay authoritative in their own modules
- read-only real market data reused for implied probability comparison
- extensible source model keeps room for future Reddit/Twitter connectors without changing current API boundary

## Prediction agent boundary (MVP)

Nuevo módulo backend `apps.prediction_agent` para separar explícitamente:
1. feature construction
2. profile selection
3. scoring/calibration
4. edge/confidence output

### Contrato de salida

Cada score persiste y expone:
- `system_probability`
- `market_probability`
- `edge = system_probability - market_probability`
- `confidence` + `confidence_level`
- `rationale`
- `model_profile_used`

### Integración con flujo existente

- Upstream natural: `research_agent` (sentimiento/presión/divergencia narrativos)
- Ajuste conservador: `learning_memory`
- Downstream inicial: `proposal_engine` (solo contexto adicional)
- No reemplaza `risk_demo`, `policy_engine`, ni `safety_guard`

### Preparación para XGBoost

Se deja separado el contrato de features/scoring/profile para permitir luego:
- exportar datasets de `PredictionFeatureSnapshot` + labels
- cargar scorer entrenado en un profile dedicado
- mantener APIs y consumers sin ruptura

## Prediction training architecture boundary

The backend keeps `apps.prediction_agent` focused on runtime scoring/inference and introduces `apps.prediction_training` for offline model lifecycle:

- `PredictionDatasetRun`: reproducible dataset metadata + artifact path
- `PredictionTrainingRun`: training execution status + validation summary
- `PredictionModelArtifact`: versioned model registry + active flag

`prediction_agent.services.scoring` checks for an active model artifact at runtime. If unavailable or inference fails, it automatically falls back to the existing heuristic profile path and records runtime mode in score details.

## Agent orchestration boundary

A dedicated orchestration boundary now exists in `apps/backend/apps/agents`.

### Goals
- make agent execution explicit and auditable
- preserve existing domain services as the execution engines
- add structured handoffs and pipeline-level traceability

### Core entities
- `AgentDefinition`
- `AgentRun`
- `AgentPipelineRun`
- `AgentHandoff`

### Service boundaries
- `registry.py`: default agent registration
- `orchestrator.py`: run lifecycle + pipeline execution wrapper
- `pipelines.py`: pipeline implementations that call existing research/prediction/risk/postmortem/learning services
- `handoffs.py`: structured handoff persistence helper

### Initial pipelines
1. `research_to_prediction`
2. `postmortem_to_learning`
3. `real_market_agent_cycle`

### Integration intent
This boundary is intentionally prepared for deeper integration with:
- `continuous_demo`
- `real_market_ops`
- `operator_queue`
- `runtime_governor`

without replacing those modules all at once.

### Explicit non-goals (current stage)
- real-money execution
- real order routing
- opaque multi-agent planner
- autonomous black-box LLM control
- distributed orchestration complexity


## Risk agent refinement (paper/demo only)
- New `apps/backend/apps/risk_agent/` module introduces structured `RiskAssessment`, `RiskSizingDecision`, `PositionWatchRun`, and `PositionWatchEvent`.
- Separation of concerns is explicit: prediction estimates; risk evaluates/sizes; policy authorizes; safety limits; runtime governs mode.
- API endpoints: `POST /api/risk-agent/assess/`, `POST /api/risk-agent/size/`, `POST /api/risk-agent/run-watch/`, `GET /api/risk-agent/assessments/`, `GET /api/risk-agent/watch-events/`, `GET /api/risk-agent/summary/`.
- Frontend route `/risk-agent` provides assessment, sizing, watch loop, and audit history panels.
- Out of scope remains unchanged: no real money, no real execution, no production-grade Kelly optimizer, no exchange stop-loss automation.

## Postmortem board architecture (new)

`apps.postmortem_agents` is a thin orchestration/synthesis boundary that reuses existing domains (`postmortem_demo`, `research_agent`, `prediction_agent`, `risk_agent`, `runtime_governor`, `safety_guard`, `operator_queue`, `learning_memory`) without duplicating their core logic.

Service split:
- `services/context.py`: gathers evidence from existing structured models
- `services/reviewers.py`: perspective-level structured reviews (optional local LLM)
- `services/conclusion.py`: final failure-mode synthesis + learning handoff
- `services/board.py`: run orchestration and persistence

This keeps postmortem multi-agent behavior explicit/auditable and avoids free-form autonomous planning.

## Research universe scan architecture (new)

The research boundary now has a dedicated **universe triage** layer on top of narrative ingestion/analysis:

1. Universe load (`Market` scope by provider/source/activity).
2. Transparent triage scoring (liquidity, volume, timing, status, freshness, narrative boost/caution).
3. Persisted decisions (`MarketTriageDecision`) per market.
4. Persisted pursuit board output (`PursuitCandidate`) for shortlist/watch.
5. Run-level audit envelope (`MarketUniverseScanRun`) with aggregated reasons and counters.

This keeps views thin and makes triage auditable and replayable.

Out of scope (unchanged): real execution, real-money ops, opaque optimizers, and LLM-final-authority flows.


## Signal fusion architecture extension

`apps.signals` now has a service split for the new board layer:
- `services/fusion.py`: consolidates research + prediction + risk + runtime/safety context
- `services/ranking.py`: deterministic opportunity ordering
- `services/gating.py`: explicit proposal pre-gate decisions
- `services/board.py`: summary aggregation for `/signals` UI

Important: fusion does not reimplement research/prediction/risk internals; it consumes their latest outputs and generates auditable upstream context for `proposal_engine` and `allocation` workflows.

## Opportunity supervisor architecture (new)

A dedicated backend module (`apps.opportunity_supervisor`) now orchestrates the last-mile opportunity lifecycle using existing domain services:

- signal fusion for research/prediction/risk convergence
- proposal engine for proposal drafts
- allocation engine for pre-execution sizing checks
- runtime governor + policy + safety for final path governance
- operator queue / paper trading for final action sink

The supervisor is **not** a replacement authority for policy/safety/runtime; it is a deterministic flow coordinator with persisted run/item/plan artifacts.

## Mission control architecture boundary (new)

A dedicated `apps/mission_control` boundary now orchestrates periodic closed-loop supervision without replacing existing domain engines.

Design intent:
- mission control orchestrates; it does not duplicate opportunity execution logic.
- `opportunity_supervisor` remains the central scan→proposal→allocation→queue/auto paper path.
- runtime governor and safety guard stay authoritative; mission control only adapts/degrades/skips based on their state.
- each cycle stores auditable step traces with explicit status/summary/details.

Primary entities:
- `MissionControlState`: singleton runtime control state and active session pointer.
- `MissionControlSession`: lifecycle scope for one autonomous operation window.
- `MissionControlCycle`: one auditable control-plane turn.
- `MissionControlStep`: explicit step-level trace within a cycle.

## Portfolio governor architecture boundary

`apps.portfolio_governor` agrega una frontera de gobernanza de cartera completa sin reemplazar capas existentes:

- **Exposure analysis:** cálculo de snapshot agregado desde `paper_trading`.
- **Regime signals:** señales simples y auditables por concentración, drawdown, capital, runtime/safety y presión operativa.
- **Throttle decision:** regla explícita de estado + multiplicador global + máximo de nuevas entradas.
- **Governance run:** traza formal persistida para auditoría y consumo por otros módulos.

Integración:
- `opportunity_supervisor` consulta throttle vigente para bloquear/degradar paths y escalar conservadurismo.
- `mission_control` incorpora `portfolio_governance_check` como paso explícito del ciclo.
- `agents` agrega `portfolio_governor_agent` y handoffs `risk -> portfolio_governor -> opportunity_supervisor`.

No implementado:
- execution real, optimizer institucional, hedging/correlación cuant compleja, decisiones opacas por LLM.

## Adaptive profile manager architecture

`apps.profile_manager` introduces a transparent meta-governance boundary above operational profile consumers.

Service split:
- `services/state.py`: aggregate state snapshot from runtime/safety/readiness/portfolio/queue signals
- `services/regime.py`: auditable rule-based regime classification
- `services/decision.py`: profile recommendation decision payload
- `services/apply.py`: explicit apply path (never bypasses runtime/safety/readiness)
- `services/governance.py`: run orchestration + run/decision persistence

Data model:
- `ProfileGovernanceRun`
- `ProfileDecision`
- `ManagedProfileBinding`
- enum `RegimeClassification`

Integration points:
- mission control cycle adds `profile_governance_check` step at cycle start
- portfolio governor remains an input (not replaced)
- runtime/safety/readiness remain higher-order authority

Non-goals unchanged: real execution, opaque planner autonomy, RL/ML meta-controller.

### Execution simulator
- Added a dedicated backend app `execution_simulator` to separate trade intent from paper execution outcomes.
- This app owns order lifecycle simulation (open/partial/filled/cancelled/expired/rejected), slippage, and no-fill handling.

## Champion-challenger shadow benchmark architecture (new)

`apps/champion_challenger` adds a conservative benchmark layer between model/profile governance and operational promotion decisions.

### Responsibilities
- define explicit champion/challenger stack bindings
- run challenger stacks in shadow mode (paper/demo only)
- compare champion vs challenger with execution-aware realism
- emit recommendation + rationale without automatic switching

### Why separate from experiment_lab?
- `experiment_lab` is strategy/profile experiment orchestration
- `champion_challenger` is continuous champion-baseline benchmarking for active-stack governance evidence
- both can reuse replay/evaluation execution-aware metrics

### Integration points
- `prediction_training`: active model artifact used in binding snapshots
- `profile_manager`: module profile defaults and runtime constraints snapshots
- `mission_control`: optional trigger cadence (`run_shadow_benchmark_every_n_cycles`)
- `readiness_lab` / governance workflows: consume evidence downstream (manual decision only)

### Explicit non-goals
- no real execution
- no automatic champion promotion
- no opaque planner authority
- no distributed orchestration layer

## Semantic memory retrieval architecture (new)

A dedicated backend boundary now exists in `apps.memory_retrieval`.

Core models:
- `MemoryDocument`: normalized memory unit with metadata + local embedding vector.
- `MemoryRetrievalRun`: auditable retrieval query record.
- `RetrievedPrecedent`: ranked similar document rows with score/reason.

Service split:
- `services/documents.py`: source-to-memory document builders.
- `services/embeddings.py`: embedding lifecycle + cosine similarity.
- `services/indexing.py`: source sync + embedding refresh orchestration.
- `services/retrieval.py`: query embedding + similarity ranking + run persistence.
- `services/precedents.py`: case-based summary synthesis.

Integration pattern:
- research/prediction/risk/postmortem apps can trigger precedent retrieval through lightweight assist endpoints.
- retrieval is contextual evidence, not an authoritative planner.

Scope guardrails:
- local-first, paper/demo only
- no real-money execution
- no external enterprise vector DB requirement

## Promotion committee architecture (new)

The new `apps.promotion_committee` app is a governance layer that **consumes** evidence from existing subsystems and does not replace them.

Key design points:
- champion/challenger remains comparative evidence producer
- readiness remains strong gate input
- profile manager + portfolio governor remain regime/throttle sources
- prediction training remains model registry authority
- memory retrieval contributes precedent warnings

Data model:
- `StackEvidenceSnapshot`
- `PromotionReviewRun`
- `PromotionDecisionLog`

Service layering:
- `evidence.py`: cross-app synthesis
- `recommendation.py`: explicit recommendation rules
- `review.py`: run orchestration + persistence
- `apply.py`: limited manual apply only
- `state.py`: current/staleness summary

Non-goals preserved:
- no real-money execution
- no automatic opaque stack switching
- no enterprise committee workflow complexity


## Rollout manager architecture (new)

A new backend module `apps/rollout_manager` introduces a conservative operational layer after promotion recommendation.

### Responsibilities
- plan definition (`StackRolloutPlan`)
- rollout execution state (`StackRolloutRun`)
- deterministic canary routing (`services/routing.py`)
- guardrail evaluation (`services/guardrails.py`)
- decision recommendation (`services/decisions.py`)
- explicit rollback (`services/rollback.py`)

### Integrations
- `promotion_committee`: source recommendation/evidence, not duplicated
- `champion_challenger`: benchmark evidence before/after rollout
- `opportunity_supervisor`: per-opportunity champion/canary route tagging + count updates
- `mission_control`: cycle details include rollout state and recommendation snapshot

### Explicit non-goals
- no real execution
- no enterprise/distributed rollout orchestration
- no opaque autonomous full switching

## Incident commander architecture (new)

`apps/incident_commander` adds a formal resilience layer above existing runtime/safety/mission/rollout services:

- `services/detection.py`: detects incident patterns from existing app data.
- `services/policies.py`: conservative rule mapping incident -> actions + degraded state.
- `services/actions.py`: executes explicit mitigations and records `IncidentAction`.
- `services/recovery.py`: bounded safe retries (`IncidentRecoveryRun`).
- `services/degraded_mode.py`: singleton-like degraded posture snapshot (`DegradedModeState`).

Authority model: `safety_guard` and `runtime_governor` constraints remain authoritative; incident commander only tightens restrictions.

## Chaos lab architecture (new)

`apps.chaos_lab` introduces a dedicated resilience-testing boundary without duplicating incident logic.

Model layer:
- `ChaosExperiment`: catalog of controlled scenarios
- `ChaosRun`: concrete execution trace
- `ChaosObservation`: per-run audit events
- `ResilienceBenchmark`: consolidated resilience metrics

Service layer:
- `services/experiments.py`: scenario catalog seeding
- `services/injection.py`: scoped fault injection against existing apps
- `services/observations.py`: detection/mitigation/degraded/rollback observation capture
- `services/benchmark.py`: transparent metric consolidation and scoring
- `services/recovery.py`: cleanup/reset of injected artifacts

Integration approach:
- reuse `incident_commander` for detection and mitigation actions
- validate reaction of `mission_control`, `rollout_manager`, alerts, notifications, and queue systems
- keep paper/demo-only boundaries and avoid real execution paths


## Certification board architecture (paper-only)

New app: `apps.certification_board`.

Service split:
- `services/evidence.py`: consolidates multi-module operational evidence into `CertificationEvidenceSnapshot`
- `services/recommendation.py`: conservative rules to derive level + recommendation + blockers + remediation
- `services/envelope.py`: translates certification into explicit `OperatingEnvelope`
- `services/review.py`: orchestrates run creation and decision logs
- `services/apply.py`: optional manual safe apply (conservative runtime mode enforcement only)

Design goals:
- wrap readiness with resilience + incidents + rollout/promotion + execution realism
- avoid logic in views
- keep full audit trail
- preserve manual-first paper-only boundaries


## Broker bridge architecture (new)

`apps.broker_bridge` formalizes the boundary between internal paper execution and future broker adapters.

Flow:
1) build `BrokerOrderIntent` from internal source (`execution_simulator` paper orders now, extendable later)
2) validate with existing authorities (certification envelope, runtime governor, safety guard, incident degraded mode)
3) create `BrokerDryRun` simulated broker response
4) enqueue operator review context for blocked/manual-review outcomes

Design principles:
- no business logic in views
- explicit service split (`intents`, `mapping`, `validation`, `dry_run`, `readiness`)
- auditable persistence at each stage
- strict non-goal: real order routing and real money execution

## go_live_gate (final pre-live boundary, still paper-only)

`go_live_gate` is a conservative orchestration layer above `broker_bridge`:

- consumes existing broker intents/dry-runs from `broker_bridge`
- uses `certification_board`, `runtime_governor`, `safety_guard`, and `incident_commander` as authoritative checklist inputs
- writes blocked rehearsal context to `operator_queue`
- enforces an explicit `capital_firewall` that keeps live transition disabled

Scope is rehearsal-only: no credentials, no live adapter, no live order transport.

## Execution venue contract layer (new)

A dedicated `apps.execution_venue` app now sits beside `broker_bridge` and below the go-live transition boundary.

Design intent:
- keep `broker_bridge` as intent/validation/dry-run orchestration
- add a stable external contract for future adapters
- provide a null/sandbox adapter implementation for deterministic local behavior
- run parity checks across internal and future external semantics without live routing

Core backend components:
- services/adapters.py: adapter contract + `NullSandboxVenueAdapter`
- services/payloads.py: canonical payload build + capability-aware validation
- services/responses.py: normalized status mapping and simulated venue responses
- services/parity.py: `VenueParityRun` creation, readiness score, and optional incident context
- services/capabilities.py: capability profile bootstrap and serialization

Hard boundary remains intact:
- `live_supported` is false
- no credentials, no real broker connections, no order transmission

## Venue account mirror / external state parity (new)

`apps.venue_account` introduces a clean, sandbox-only inbound bridge layer:

- snapshot builders (`services/snapshots.py`) normalize external-style account/order/position/balance state.
- mirror orchestration (`services/mirror.py`) refreshes canonical external snapshots.
- reconciliation engine (`services/reconciliation.py`) compares internal paper state vs mirror state and persists issues.
- issue logging (`services/issues.py`) keeps reconciliation findings explicit and auditable.
- summary/state helpers (`services/state.py`) provide lightweight dashboard/go-live consumption paths.

Design boundary:
- complements `execution_venue` (send-side contract) instead of duplicating it.
- uses `broker_bridge`, `execution_simulator`, and `paper_trading` artifacts as source evidence.
- remains local-first and sandbox-only; no live connectors.

## Connector lab architecture (new)

`apps.connector_lab` introduces a formal certification boundary for future venue adapters.

Design goals:
- separate adapter contract qualification from runtime execution paths
- keep qualification logic in services (not views)
- produce auditable run/results/recommendation entities
- reuse existing `execution_venue` and `venue_account` workflows for payload/response/parity evidence

Main entities:
- `AdapterQualificationRun`
- `AdapterQualificationResult`
- `AdapterReadinessRecommendation`
- `ConnectorFixtureProfile`

This boundary is intentionally pre-integration: it does not open any real read-only/live connectivity.

## Trace explorer provenance boundary (new)

`apps.trace_explorer` introduces a dedicated cross-cutting provenance boundary to unify traceability without modifying existing execution domains.

Architecture characteristics:
- **Aggregator, not replacement**: consumes existing app records and composes an operational narrative.
- **Explicit primitives**: `TraceRoot`, `TraceNode`, `TraceEdge`, `TraceQueryRun`.
- **Service-oriented composition**:
  - root resolution
  - node harvesting across modules
  - causal/handoff edge building
  - compact provenance snapshot generation
  - query-run auditing
- **Operational goal**: explain *why* a case reached its state (e.g., `PROPOSAL_READY`, blocked, degraded, executed).

Non-goals remain strict:
- no live money/execution
- no distributed enterprise graph
- no opaque planner authority


## Runbook engine (guided remediation layer)

`apps.runbook_engine` is an orchestration/audit layer above specialized operational modules.

Responsibilities:
- Keep reusable runbook templates
- Instantiate source-linked runbooks
- Execute and track step progression
- Reuse existing APIs/services (mission control, incidents, rollout, certification, venue account reconciliation, trace)
- Store per-step action outcomes/evidence
- Produce summary + deterministic recommendations

Out of scope:
- real-money or live execution
- opaque autonomous planner behavior
- enterprise multi-user workflow complexity

## Trust-tiered automation policy layer (new)

A dedicated `apps.automation_policy` app now provides a formal and auditable policy matrix for supervised automation.

### Responsibility split
- `runbook_engine`: workflow sequencing and step lifecycle.
- `automation_policy`: evaluate whether actions are auto-allowed, approval-required, manual-only, or blocked.
- `runtime_governor`, `safety_guard`, `certification_board`, `incident_commander`: authority layers that can downgrade effective trust.

### Internal services
- `services/profiles.py`: active profile resolution and profile switching.
- `services/rules.py`: explicit policy rule matrix by action/context.
- `services/guardrails.py`: effective tier downgrade from runtime/safety/certification/degraded posture.
- `services/decisions.py`: decision creation + reason codes.
- `services/execution.py`: controlled execution/logging path for allowed actions.

### Audit model
- `AutomationPolicyProfile`
- `AutomationPolicyRule`
- `AutomationDecision`
- `AutomationActionLog`

This layer is intentionally conservative: local-first, single-user, paper/sandbox only, and explicitly blocks live execution domains.

## Runbook autopilot architecture (new)

`runbook_engine` now has a thin supervised orchestration layer over existing runbook workflows.

### Responsibility split
- `runbook_engine` remains workflow/template/step execution authority.
- `automation_policy` remains trust-tier and guardrail authority.
- `autopilot` only sequences steps, asks policy, executes allowed actions, and pauses/blocks when needed.

### Core entities
- `RunbookAutopilotRun`: lifecycle + counters + summary for one orchestration run.
- `RunbookAutopilotStepResult`: per-step outcome + attempt + links to automation/runbook evidence.
- `RunbookApprovalCheckpoint`: explicit approval pause artifact with context snapshot.

### Service boundaries
- `runbook_engine.services.autopilot`: start/resume/retry loop.
- `runbook_engine.services.orchestration`: counters and summary updates.
- `runbook_engine.services.approvals`: checkpoint create/resolve.
- `automation_policy.services.runbook_resolution`: step-level policy decision projection for autopilot.

This keeps the system auditable, manual-first, and conservative while enabling gradual supervised auto-advance.

## Approval center architecture (new)

A new backend module `approval_center` acts as a **normalization and control plane**, not as a replacement of source-domain models.

Design:
- Source adapters (`services/sources.py`) map runbook/go-live/operator queue objects into normalized `ApprovalRequest` records.
- Decision engine (`services/decisions.py`) applies manual actions and dispatches side effects back to source modules.
- Impact layer (`services/impact.py`) provides auditable action previews.
- Request/sync + queue views (`services/requests.py`, `services/summary.py`) power list/detail/pending/summary endpoints.

Why this is conservative:
- source of truth remains in each module
- approval center keeps lifecycle + audit continuity across modules
- no live money/execution behavior introduced


## Trust calibration architecture boundary

`apps.trust_calibration` is an analytics/governance boundary that **does not** replace `automation_policy` authority.

Flow:
1. ingest historical approvals (`approval_center`)
2. ingest policy decisions + action logs (`automation_policy`)
3. join runbook/profile/source context where available
4. fold in incident-after-auto signals (`incident_commander`)
5. persist auditable run + feedback snapshots + recommendations

Design constraints:
- explicit rules and formulas (no black-box learning)
- recommendation-only by default
- policy updates remain explicit human decisions
- local-first, single-user, paper/sandbox only

## policy_tuning boundary (new)

`policy_tuning` is the supervised automation tuning boundary between recommendation generation and policy mutation.

- Consumes: `trust_calibration.TrustCalibrationRecommendation`
- Produces: `PolicyTuningCandidate` + `PolicyChangeSet` + `PolicyTuningReview` + `PolicyTuningApplicationLog`
- Mutates only through explicit manual apply: `automation_policy.AutomationPolicyRule`
- Uses `approval_center` for consistent manual decision visibility
- Preserves recommendation-only posture in trust calibration and manual-first policy authority


## Autonomy manager architecture (new)

`apps.autonomy_manager` is a domain-level orchestration layer that sits above action-level policy governance.

Core entities:
- `AutonomyDomain`: operational domain and action mapping
- `AutonomyEnvelope`: per-domain operational limits
- `AutonomyStageState`: current/effective stage posture
- `AutonomyStageRecommendation`: evidence-backed recommendation output
- `AutonomyStageTransition`: manual-first transition lifecycle (approval/apply/rollback)

Service split:
- `services/domains.py`: domain seed catalog and mapping to action types
- `services/evidence.py`: trust/rollout/incident/approval/certification evidence consolidation
- `services/recommendation.py`: deterministic recommendation policy (no black-box planner)
- `services/transitions.py`: transition generation + approval-aware apply/rollback
- `services/envelopes.py`: envelope projection

Boundary contracts:
- `automation_policy` remains source-of-truth at rule/action granularity
- `policy_tuning` and `policy_rollout` remain change-detail and post-change loops
- `autonomy_manager` governs staged posture across coherent domains

## `autonomy_rollout` post-change layer

`autonomy_rollout` is a narrow, auditable boundary that observes the impact of an **applied** domain stage transition.

- Depends on `autonomy_manager` for transition lifecycle (does not replace stage recommendation/apply logic).
- Reuses trust/policy-like metrics semantics for baseline/post snapshots.
- Adds conservative cross-domain warning signals from incident/degraded posture context.
- Keeps rollback manual-first by delegating rollback execution to `autonomy_manager.services.transitions.rollback_transition` and optionally opening approval gates in `approval_center`.

Service split:
- `services/baseline.py`: baseline snapshot creation per domain action scope
- `services/observation.py`: post-change snapshot capture
- `services/comparison.py`: metric delta computation
- `services/recommendation.py`: recommendation-first outcome
- `services/rollback.py`: manual rollback orchestration + audit payload
- `services/reporting.py`: cockpit/board summary

## Autonomy roadmap architecture (new)

A dedicated `apps.autonomy_roadmap` module introduces a formal cross-domain governance layer:

- `autonomy_manager` keeps domain transition authority.
- `autonomy_rollout` keeps per-domain post-change observation authority.
- `autonomy_roadmap` provides **global sequencing intelligence** with explicit dependency rules.

Modeling primitives:
- dependency graph (`DomainDependency`)
- domain criticality (`DomainRoadmapProfile`: LOW/MEDIUM/HIGH/CRITICAL)
- global plan snapshot (`AutonomyRoadmapPlan`)
- recommendation ledger (`RoadmapRecommendation`)
- optional sequencing bundles (`RoadmapBundle`)

Recommendation strategy is deterministic and auditable:
- consolidate stage state, rollout warnings, degraded posture, approval friction, trust/certification signals
- classify actions (`PROMOTE_DOMAIN`, `FREEZE_DOMAIN`, `ROLLBACK_DOMAIN`, `SEQUENCE_BEFORE`, `DO_NOT_PROMOTE_IN_PARALLEL`, `REQUIRE_STABILIZATION_FIRST`)
- persist recommendations and bundles under one plan ID

Safety boundary is explicit: no multi-domain auto-apply, no opaque planner, no real-money/real-execution expansion.


## Autonomy scenario architecture (new)

`autonomy_scenario` is a comparative simulation boundary between roadmap planning and transition apply:

- **Input sources**: `DomainDependency`, `AutonomyStageState`, latest roadmap recommendations, rollout warnings, approval summary, trust friction, incident/degraded posture
- **Core services**:
  - `services/options.py`: scenario option drafting
  - `services/risk.py`: risk and conflict estimation
  - `services/recommendation.py`: scenario recommendation coding/scoring
  - `services/simulation.py`: run orchestration + persistence
  - `services/reporting.py`: summary/list endpoints
- **Persistence**: `AutonomyScenarioRun`, `ScenarioOption`, `ScenarioRiskEstimate`, `ScenarioRecommendation`
- **Output contract**: recommendation-first and auditable; never applies transitions

Separation of concerns:
- roadmap proposes global plans/bundles
- scenario lab compares alternatives
- autonomy manager remains the only apply boundary
- autonomy rollout remains post-change monitoring/rollback guidance


## Autonomy campaign orchestration boundary

`autonomy_campaign` is an orchestration boundary, not a replacement for autonomy transition engines:

- owns campaign program lifecycle (`DRAFT/READY/RUNNING/PAUSED/BLOCKED/COMPLETED/ABORTED/FAILED`)
- owns step/checkpoint progression and audit metadata
- calls into `autonomy_manager` for actual stage transition apply
- calls into `autonomy_rollout` for post-apply monitor lifecycle
- binds into `approval_center` for approval-required checkpoints

This keeps recommendation/simulation modules (`autonomy_roadmap`, `autonomy_scenario`) decoupled from execution sequencing while preserving traceability and manual control.

## Autonomy program governance architecture (new)

`apps.autonomy_program` is a program-level control layer above `autonomy_campaign`.

Design intent:
- keep campaign execution semantics inside `autonomy_campaign` (steps/waves/checkpoints)
- add cross-campaign program governance for safe coexistence and operational health

Core models:
- `AutonomyProgramState`
- `CampaignConcurrencyRule`
- `CampaignHealthSnapshot`
- `ProgramRecommendation`

Service split:
- `services/state.py`: consolidate global posture and lock/concurrency metadata
- `services/rules.py`: explicit concurrency rules + conflict detection
- `services/health.py`: campaign health snapshots from checkpoints/approvals/rollout/incidents/degraded
- `services/recommendation.py`: recommendation emission from posture + conflicts + health
- `services/control.py`: `run_program_review` orchestration + optional pause gating + approval request handoff

Integration points:
- `autonomy_campaign`: reads campaign + step/checkpoint state and can mark campaign `BLOCKED` via pause gate
- `autonomy_rollout`: consumes rollout warning/freeze/rollback signals
- `incident_commander`: consumes critical/degraded posture signals
- `approval_center`: opens high-impact pause approval requests
- `trace_explorer`: remains downstream drill-down layer via linked roots

Non-goals:
- no replacement of campaign internals
- no opaque auto-planner or mass auto-apply
- no real-money/real-execution pathways

## Autonomy scheduler architecture (new)

`apps.autonomy_scheduler` adds a conservative admission-governance layer for campaign intake.

### Responsibilities
- Queue consolidation for campaign candidates (`services/queue.py`)
- Safe-start window resolution (`services/windows.py`)
- Simple visible scoring (`services/prioritization.py`)
- Explicit block/defer/ready admission evaluation (`services/admission.py`)
- Auditable planning runs + recommendation generation (`services/planning.py`)
- Manual apply controls (admit/defer + optional approval request) (`services/control.py`)

### Integration boundaries
- Consumes `autonomy_program` posture/health constraints as superior authority.
- Consumes `autonomy_campaign` metadata/dependencies and does not execute campaign waves.
- May open `approval_center` requests for sensitive admits.
- Surfaces explicit block reasons for incidents/degraded/locked domains/window constraints.

### Non-goals
- No auto-start orchestration engine.
- No distributed scheduler.
- No black-box optimization or ML planner.
- No real-money execution scope.


## Autonomy launch start-gate architecture (new)

`apps.autonomy_launch` introduces a conservative, auditable layer between campaign admission and campaign start.

Service split:
- `services/candidates.py`: admitted/ready launch candidate selection
- `services/preflight.py`: explicit preflight checks (posture/window/conflicts/dependencies/approvals/incidents/degraded/rollout pressure)
- `services/readiness.py`: snapshot + simple readiness scoring
- `services/recommendation.py`: recommendation emission (`START_NOW`, `HOLD`, `WAIT`, `BLOCK`, `REORDER`)
- `services/authorization.py`: formal authorization records + approval request linkage when needed
- `services/control.py`: manual-first authorize/hold actions

Boundary rules:
- does not replace scheduler queue/admit/defer
- does not replace program concurrency authority
- does not replace campaign execution engine
- does not implement opaque auto-start orchestration

## Autonomy activation gateway architecture (new)

`apps.autonomy_activation` provides the final manual-first dispatch boundary:

- **Inputs:** launch authorizations (`autonomy_launch`), queue/window posture (`autonomy_scheduler`), global posture/conflicts (`autonomy_program`), incident/degraded context (`incident_commander`)
- **Core flow:** candidates -> revalidation -> recommendation -> dispatch handoff -> outcome persistence
- **Dispatch target:** `autonomy_campaign.services.start_campaign`
- **Audit artifacts:**
  - `CampaignActivation` for attempt/outcome lifecycle
  - `ActivationRun` for review snapshots
  - `ActivationRecommendation` for explainable dispatch guidance

This keeps launch readiness and scheduler admission separate from final dispatch execution while preserving conservative, explainable controls.

## Autonomy operations runtime supervision architecture (new)

`apps.autonomy_operations` adds a formal, auditable runtime monitoring layer for active campaigns **after** activation/start.

Model set:
- `CampaignRuntimeSnapshot`
- `CampaignAttentionSignal`
- `OperationsRun`
- `OperationsRecommendation`

Design intent:
- consume runtime context from `autonomy_campaign` (+ rollout/incidents/approvals signals)
- classify runtime status explicitly (`ON_TRACK`, `CAUTION`, `STALLED`, `BLOCKED`, `WAITING_APPROVAL`, `OBSERVING`)
- emit recommendation-first, manual-first operational guidance
- keep orchestration transparent and deterministic (no ML/LLM authority)

Integration boundaries:
- `autonomy_campaign`: remains step/wave/checkpoint execution authority
- `autonomy_activation`: remains dispatch/start handoff authority
- `autonomy_program`: remains global multi-campaign posture authority
- `approval_center`/`incident_commander`/`autonomy_rollout`: influence runtime pressure and signals

Non-goals remain:
- real-money execution
- broker/exchange routing
- opaque auto-remediation
- distributed enterprise orchestration


## Autonomy intervention control layer (new)

`apps.autonomy_intervention` is the formal manual remediation gateway for active campaigns.

Data model:
- `CampaignInterventionRequest`: intervention intent, status, rationale, blockers, source linkage.
- `CampaignInterventionAction`: execution attempt + operational result envelope.
- `InterventionOutcome`: explicit before/after state outcome record.
- `InterventionRun`: periodic review summary for the intervention board.

Integration boundaries:
- consumes `autonomy_operations` recommendations/signals (does not replace monitoring).
- invokes minimal `autonomy_campaign` controls for pause/resume flows.
- respects `autonomy_program` posture constraints (`FROZEN` blocks non-conservative actions).
- opens `approval_center` requests for sensitive intervention actions.
- preserves traceability via campaign/approval/trace linkable metadata and IDs.

## Autonomy recovery architecture (new)

`apps.autonomy_recovery` is the formal paused-campaign resolution layer.

Service split:
- `services/candidates.py`: campaign candidate selection (paused/blocked/intervened context)
- `services/blockers.py`: blocker aggregation (approvals, checkpoints, incidents, program posture/domain locks)
- `services/readiness.py`: deterministic score/readiness/status evaluation
- `services/recommendation.py`: recommendation emission per snapshot
- `services/control.py`: manual-first approval request helpers (resume/close)
- `services/run.py`: auditable orchestration of snapshots + run summary + recommendations

Model layer:
- `RecoverySnapshot`: per-campaign recovery state snapshot
- `RecoveryRun`: aggregate run summary for one review cycle
- `RecoveryRecommendation`: explicit disposition guidance records

Integration boundaries:
- consumes intervention outcomes and campaign/runtime context
- respects `autonomy_program` as global posture authority
- routes sensitive actions through `approval_center`
- leaves actual pause/resume/abort execution to intervention/campaign flows
- keeps traceability through campaign identifiers and recommendation metadata


## Autonomy disposition architecture (new)

`apps.autonomy_disposition` adds a conservative closure committee layer after active campaign operations:

- **Input context:** latest recovery snapshot, latest intervention outcome, latest runtime snapshot, pending approvals/checkpoints, unresolved incident pressure.
- **Decision artifacts:**
  - `CampaignDisposition` (formal final disposition decision)
  - `DispositionRun` (auditable consolidation run)
  - `DispositionRecommendation` (explicit close/abort/retire/keep-open recommendations)
- **Service split:**
  - `services/candidates.py`: candidate selection/context hydration
  - `services/readiness.py`: readiness + closure risk + blockers
  - `services/recommendation.py`: deterministic recommendation and disposition mapping
  - `services/run.py`: run creation + recommendation summary
  - `services/control.py`: approval request and manual apply controls
  - `services/apply.py`: auditable state transition apply (manual-first)

Boundary rules:
- does not replace `autonomy_recovery` evaluation or `autonomy_intervention` runtime actions
- does not replace `autonomy_campaign` engine or `autonomy_program` posture authority
- no opaque auto-close/auto-abort/auto-retire and no real execution path


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

## Autonomy closeout → followup handoff boundary (new)

A dedicated `apps.autonomy_followup` app now governs knowledge-routing after closeout:

- **Input:** `CampaignCloseoutReport` from `autonomy_closeout`
- **Output:** auditable `CampaignFollowup` records + `FollowupRun` review snapshots + `FollowupRecommendation` guidance
- **Service split:**
  - `services/candidates.py` (candidate selection/readiness)
  - `services/dedup.py` (duplicate avoidance)
  - `services/recommendation.py` (deterministic recommendation rules)
  - `services/emission.py` (artifact/request creation and linkage)
  - `services/control.py` (manual-first campaign emission)
  - `services/run.py` (run consolidation + recommendation summary)

Integration contracts are explicit and conservative:
- memory handoff writes `memory_retrieval.MemoryDocument`
- postmortem handoff writes `approval_center.ApprovalRequest` stub for board routing
- roadmap/scenario feedback writes a persisted feedback artifact id stub in closeout metadata

No ML authority, no auto-apply roadmap updates, no live execution integrations.

## Autonomy feedback architecture (new)

`apps.autonomy_feedback` is the post-emission governance layer for campaign follow-ups. It does not emit follow-ups; it tracks whether emitted handoffs were actually resolved.

Service split:
- `services/candidates.py`: selects emitted follow-ups as tracking candidates.
- `services/status.py`: explicit downstream status derivation from linked memory/postmortem/feedback artifacts.
- `services/recommendation.py`: review/complete/manual/pending/reorder recommendation generation.
- `services/control.py`: manual completion controls (`complete/<followup_id>`).
- `services/run.py`: auditable run consolidation + summary counters.

Key boundary:
- explicit/manual-first rules only, no ML/LLM authority, no automatic roadmap/scenario application.

## Autonomy insights architecture (new)

`apps.autonomy_insights` is a conservative synthesis boundary layered after campaign lifecycle closure.

### Inputs
- `autonomy_closeout`: campaign dossier + findings
- `autonomy_followup`: emitted handoffs
- `autonomy_feedback`: follow-up resolution state
- `autonomy_disposition`: final disposition posture

### Service split
- `services/candidates.py`: lifecycle-closed candidate derivation
- `services/synthesis.py`: per-campaign evidence consolidation
- `services/patterns.py`: deterministic cross-campaign pattern extraction
- `services/recommendation.py`: recommendation mapping
- `services/control.py`: manual review controls
- `services/run.py`: auditable synthesis run orchestration and summary counters

### Guardrails
- lifecycle must be closed before synthesis
- pending key follow-ups block synthesis for that campaign
- recommendation-first outputs only (no auto-apply)
- no ML/LLM authority in decision logic


## Autonomy advisory resolution architecture

`autonomy_advisory_resolution` is the formal post-emission governance boundary for advisory artifacts:

- candidate selection uses emitted/blocked `AdvisoryArtifact` records from `autonomy_advisory`
- status evaluation uses explicit deterministic rules (no ML/LLM authority)
- manual control endpoints persist acknowledgment/adoption/defer/reject decisions in `AdvisoryResolution`
- run review produces `AdvisoryResolutionRun` counters and `AdvisoryResolutionRecommendation` queue

This layer never emits new advisory artifacts and never auto-applies roadmap/scenario/program/manager changes. It only tracks and audits downstream resolution state.

## Autonomy backlog architecture (new)

`apps.autonomy_backlog` is the formal governance handoff layer after `autonomy_advisory_resolution`.

### Inputs
- `autonomy_advisory.AdvisoryArtifact`
- `autonomy_advisory_resolution.AdvisoryResolution` (`ADOPTED`/`ACKNOWLEDGED` candidate states)
- linked insight/campaign lineage from `autonomy_insights` and `autonomy_campaign`

### Persistent entities
- `GovernanceBacklogItem`
- `BacklogRun`
- `BacklogRecommendation`

### Service split
- `services/candidates.py`: candidate selection + readiness/blockers
- `services/dedup.py`: duplicate detection by advisory artifact
- `services/prioritization.py`: deterministic priority level assignment
- `services/recommendation.py`: CREATE/PRIORITIZE/DEFER/SKIP/REVIEW/REORDER recommendations
- `services/control.py`: manual actions (`create_backlog_item`, `mark_prioritized`, `mark_deferred`)
- `services/run.py`: auditable review run consolidation

### Boundary guarantees
- does not replace advisory or advisory_resolution
- does not re-emit advisory notes
- does not auto-apply roadmap/scenario/program/manager updates
- explicit/manual-first, local-first, paper/sandbox only


## `autonomy_intake` backend layer (new)

`apps.autonomy_intake` consumes formal `GovernanceBacklogItem` records from `autonomy_backlog` and creates governed `PlanningProposal` artifacts for roadmap/scenario/program/manager/operator review destinations.

Design constraints:
- recommendation-first and manual-first actions (`run-review`, explicit `emit`, optional `acknowledge`)
- no opaque auto-apply to destination modules
- explicit dedup by `backlog_item + target_scope`
- auditable runs (`IntakeRun`) and recommendation history (`IntakeRecommendation`)

## `autonomy_planning_review` backend layer (new)

`apps.autonomy_planning_review` se ubica **después de** `autonomy_intake` y agrega una frontera de gobernanza para resolución posterior de planning proposals.

### Responsabilidades
- consumir proposals ya emitidas/ready/acknowledged/blocked desde `autonomy_intake`
- derivar `downstream_status` y `ready_for_resolution` con reglas explícitas (sin ML/LLM)
- persistir `PlanningProposalResolution` de forma auditable
- exponer acciones manual-first (`acknowledge`, `accept`, `defer`, `reject`)
- registrar `PlanningReviewRun` + `PlanningReviewRecommendation`

### Integración
- fuente: `autonomy_intake.PlanningProposal`
- vínculos de trazabilidad: backlog/advisory/insight/campaign
- destino: tracking de resolución (no auto-apply)

### Garantías de diseño
- evita duplicar cierres cuando ya existe `ACCEPTED`/`CLOSED`
- distingue `ACKNOWLEDGED` vs `ACCEPTED`
- permite `UNKNOWN/PENDING` cuando falta señal downstream
- conserva modelo local-first, single-user, sandbox/paper-only

## `autonomy_decision` architecture (new)

`apps.autonomy_decision` se ubica entre `autonomy_planning_review` y la ejecución manual posterior sobre roadmap/scenario/program/manager.

Cadena de trazabilidad preservada:
`campaign → insight → advisory → backlog → intake → planning_review(ACCEPTED) → decision`.

Split de servicios:
- `candidates.py`: accepted proposals candidatas
- `dedup.py`: control de duplicado por proposal/scope
- `recommendation.py`: reglas determinísticas de recomendación
- `registration.py`: persistencia de governance decision package/note
- `control.py`: endpoints manuales (register/acknowledge)
- `run.py`: run auditable y summary

Garantías:
- sin ML/LLM autoritativo
- sin auto-apply opaco
- sin mutaciones automáticas de módulos destino
- local-first, single-user, paper/sandbox only

## `autonomy_package` architecture (new)

`apps.autonomy_package` agrega una capa formal entre `autonomy_decision` y la próxima iteración de planificación.
No reemplaza `autonomy_decision`; lo consume.

### Modelos
- `GovernancePackage`: bundle persistido y auditable, con `package_type`, `package_status`, `target_scope`, `grouping_key`, `linked_decisions`.
- `PackageRun`: corrida auditable de consolidación y métricas.
- `PackageRecommendation`: recomendaciones explícitas para register/skip/manual review/reorder.

### Servicios
- `candidates.py`: selecciona decisiones `REGISTERED/ACKNOWLEDGED` listas para packaging.
- `grouping.py`: agrupación por `target_scope + grouping_key` y prioridad.
- `dedup.py`: detecta duplicates con `grouping_key + target_scope`.
- `recommendation.py`: recomendaciones transparentes por target y estado.
- `registration.py`: crea `GovernancePackage` y enlaza decisiones de origen.
- `control.py`: API manual-first para registrar package por decisión.
- `run.py`: ejecuta revisión, registra recomendaciones y consolida summary.

### Restricciones
- no dinero real
- no ejecución real broker/exchange
- no auto-apply opaco a roadmap/scenario/program/manager

## Autonomy package review architecture (new)

`autonomy_package_review` extends the autonomy governance chain after package registration:

1. `autonomy_package` registers and deduplicates `GovernancePackage` bundles.
2. `autonomy_package_review` consumes those bundles as review candidates.
3. `services/status.py` derives explicit downstream state and readiness.
4. `services/run.py` creates auditable `PackageReviewRun` snapshots and recommendations.
5. `services/control.py` applies manual-first actions (acknowledge/adopt/defer/reject) without auto-applying roadmap/scenario/program/manager changes.

This keeps a closed, traceable loop from decision packaging to package resolution while preserving conservative governance boundaries.

## Autonomy seed architecture (new)

`autonomy_seed` is the formal boundary after package adoption:

`campaign → insight → advisory → backlog → intake → planning_review → decision → package → package_review(ADOPTED) → seed`

### Data model
- `GovernanceSeed`: persistent planning seed artifact linked to `governance_package` + `package_resolution`
- `SeedRun`: auditable review pass summary
- `SeedRecommendation`: recommendation-first output queue

### Service split
- `services/candidates.py`: selects ADOPTED package resolutions and builds seed candidates
- `services/dedup.py`: duplicate guard by package + target scope
- `services/recommendation.py`: deterministic recommendation mapping by target scope/blockers
- `services/registration.py`: seed persistence construction (no downstream mutation)
- `services/control.py`: manual-first register action with explicit policy checks
- `services/run.py`: run orchestration + recommendation summary counters

### Governance boundary
- consumes `autonomy_package_review`, does not replace it
- no re-registration of packages
- no automatic mutation of roadmap/scenario/program/manager
- output is explicit reusable seed artifacts for next-cycle planning input

## Autonomy seed review architecture (new)

`apps.autonomy_seed_review` is a post-registration governance boundary:

- input: `autonomy_seed.GovernanceSeed`
- output: `SeedResolution`, `SeedReviewRun`, `SeedReviewRecommendation`

Service split:
- `services/candidates.py`: candidate projection from registered seeds
- `services/status.py`: explicit downstream status + readiness rules
- `services/recommendation.py`: recommendation-first action guidance
- `services/control.py`: manual acknowledge/accept/defer/reject actions
- `services/run.py`: auditable run consolidation + recommendation summary

Boundary:
- seed registration remains in `autonomy_seed`
- no roadmap/scenario/program/manager auto-mutation
- local-first, single-user, paper/sandbox-only scope

## Scan-agent filter hardening architecture (new)

A scan hardening layer now lives inside `apps.research_agent` and is exposed via `/api/scan-agent/*`.

Design intent:
- strengthen pre-triage scan/filter quality
- preserve `research_agent` triage/pursuit as downstream authority
- avoid opaque planner behavior

Auditable entities:
- `SourceScanRun`
- `NarrativeSignal`
- `NarrativeCluster`
- `ScanRecommendation`

Pipeline:
1. `source_fetch` collects RSS/Reddit/X items via existing adapters
2. `dedup` removes repeated narrative payloads
3. `clustering` groups equivalent themes
4. `scoring` computes explicit conservative metrics
5. `market_context` compares narrative direction with market probabilities
6. `recommendation` emits recommendation-first handoff actions
7. `run` persists run + cluster + signal + recommendation artifacts

Non-goals unchanged: no real-time social firehose, no real-money execution, no auto-apply black-box planner.
