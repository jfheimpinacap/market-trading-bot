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
- `apps.agents`: reserved for later agent orchestration work.
- `apps.audit`: reserved for later audit and post-mortem persistence.

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

## API conventions
- All endpoints live under `/api/`.
- `config/api.py` is the single place where app endpoints are mounted.
- Each app owns its own URL patterns and request/response serializers.
- The health endpoint is kept intentionally lightweight and configuration-oriented.
- Market endpoints are read-only and currently optimized for local catalog browsing.
- Paper trading endpoints are intentionally simple and assume a single active demo account by default.
- Market list and detail serializers intentionally differ so that lists stay lightweight while detail views include rules and recent snapshots.

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
- `test.py` uses SQLite and eager Celery execution for lightweight test runs.
- Environment variables control PostgreSQL, Redis, hosts, CORS, and runtime profile.

## Celery strategy
- Celery is initialized in `config/celery.py`.
- Redis is the default broker/result backend via environment variables.
- Apps can add `tasks.py` incrementally; Celery autodiscovery is already enabled.
- Real ingestion or sync tasks are intentionally deferred to a later stage.

## Growth guidelines
- Add business models only when a domain scope is ready.
- Keep shared code in `apps/common` small and reusable.
- Prefer explicit app boundaries instead of deeply nested internal frameworks.
- Avoid cross-app coupling until domain workflows become concrete.
- Extend the paper trading domain next with richer portfolio history, better summaries, optional auth, and frontend trading workflows while keeping the current demo-only execution model.
