# Backend architecture

## Overview
The backend is a local-first Django service inside the monorepo. Its current responsibility is to provide a clean, maintainable API foundation for future market, agent, audit, and execution capabilities.

## Main layers
- `config/`: global project wiring such as settings, API aggregation, root URLs, ASGI/WSGI, and Celery.
- `apps/`: Django apps grouped by bounded responsibility.
- `apps/common/`: reusable technical primitives shared across future domain apps.
- `apps/*/urls.py`: per-app route registration.
- `apps/*/views.py` and `serializers.py`: DRF endpoint and payload boundaries.

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

## Celery strategy
- Celery is initialized in `config/celery.py`.
- Redis is the default broker/result backend via environment variables.
- Apps can add `tasks.py` incrementally; Celery autodiscovery is already enabled.

## Growth guidelines
- Add business models only when a domain scope is ready.
- Keep shared code in `apps/common` small and reusable.
- Prefer explicit app boundaries instead of deeply nested internal frameworks.
- Avoid cross-app coupling until domain workflows become concrete.
