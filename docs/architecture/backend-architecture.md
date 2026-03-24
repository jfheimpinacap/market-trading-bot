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
