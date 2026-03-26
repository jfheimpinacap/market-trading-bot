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
