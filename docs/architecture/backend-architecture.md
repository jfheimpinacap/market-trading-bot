# Backend architecture

## Overview
The backend is a local-first Django service inside the monorepo. Its current responsibility is to provide a clean, maintainable API foundation for future market, agent, audit, and execution capabilities.

## Main layers
- `config/`: global project wiring such as settings, API aggregation, root URLs, ASGI/WSGI, and Celery.
- `apps/`: Django apps grouped by bounded responsibility.
- `apps/common/`: reusable technical primitives shared across future domain apps.
- `apps/*/urls.py`: per-app route registration.
- `apps/*/views.py` and `serializers.py`: DRF endpoint and payload boundaries.

## Current backend app roles
- `apps.common`: abstract timestamped models and shared technical helpers.
- `apps.health`: lightweight environment-oriented health endpoint.
- `apps.markets`: initial prediction-market catalog domain with provider, event, market, market snapshot, and market rule models plus small read-only endpoints.
- `apps.agents`: reserved for later agent orchestration work.
- `apps.audit`: reserved for later audit and post-mortem persistence.

## Market domain shape
The current `apps.markets` app is intentionally provider-agnostic.

Core relationships:
- `Provider` is the root source entity.
- `Event` groups related markets from a provider.
- `Market` represents the tradeable/analyzable market definition.
- `MarketSnapshot` stores time-series observations for a market.
- `MarketRule` stores fuller rule/resolution text separately from the market summary row.

This gives the backend a clean relational base before adding provider sync, signals, or paper trading layers.

## Settings strategy
- `base.py` contains shared defaults.
- `local.py` keeps local development behavior simple.
- `test.py` uses SQLite and eager Celery execution for lightweight test runs.
- Environment variables control PostgreSQL, Redis, hosts, CORS, and runtime profile.

## API conventions
- All endpoints live under `/api/`.
- `config/api.py` is the single place where app endpoints are mounted.
- Each app owns its own URL patterns and request/response serializers.
- The health endpoint is kept intentionally lightweight and configuration-oriented.
- Current market endpoints are read-only and intended for inspection rather than business workflows.

## Celery strategy
- Celery is initialized in `config/celery.py`.
- Redis is the default broker/result backend via environment variables.
- Apps can add `tasks.py` incrementally; Celery autodiscovery is already enabled.

## Growth guidelines
- Add business models only when a domain scope is ready.
- Keep shared code in `apps/common` small and reusable.
- Prefer explicit app boundaries instead of deeply nested internal frameworks.
- Avoid cross-app coupling until domain workflows become concrete.
- Extend the market domain next with provider ingestion and snapshot capture before trading workflows.
