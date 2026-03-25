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
- `apps.signals`: demo-only signals domain with mock agents, signal runs, heuristic generation, admin tooling, and read-only DRF endpoints.
- `apps.postmortem_demo`: demo-only trade review domain that evaluates executed paper trades after the fact and exposes read-only review endpoints.
- `apps.agents`: reserved for later agent orchestration work.
- `apps.audit`: reserved for later audit and post-mortem persistence.
- `apps.policy_engine`: demo-only governance boundary that converts trade proposals into explicit approval outcomes.
- `apps.experiment_lab`: profile-driven experiment orchestration layer that reuses replay/evaluation services and produces auditable run comparisons.

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
