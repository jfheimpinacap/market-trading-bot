# Backend Django API

Backend base for the `market-trading-bot` monorepo. This service is intentionally local-first and currently focuses on clean project structure, a practical prediction-market catalog, and a smooth local workflow.

## Current purpose
- Provide a modular Django + DRF API base inside the monorepo.
- Keep a stable local development setup for PostgreSQL, Redis, Celery, and the frontend.
- Expose a lightweight healthcheck at `/api/health/`.
- Provide a provider-agnostic market domain for catalog, metadata, rule text, and snapshot history work.
- Make it easy to seed realistic demo data locally for admin and frontend development.

## Internal structure

```text
apps/backend/
├── apps/
│   ├── agents/
│   ├── audit/
│   ├── common/
│   ├── health/
│   └── markets/
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
- `apps.markets`: provider, event, market, market snapshot, and market rule models plus demo seeding, admin tooling, and read-only API endpoints.
- `apps.agents`: placeholder app for future agent domain work.
- `apps.audit`: placeholder app for future audit and post-mortem work.

## Markets app summary
The `apps.markets` app now provides a practical local catalog for prediction-market development without adding trading workflows or provider integrations.

Current market models:
- `Provider`
- `Event`
- `Market`
- `MarketSnapshot`
- `MarketRule`

Current read-only market endpoints:
- `/api/markets/providers/`
- `/api/markets/events/`
- `/api/markets/`
- `/api/markets/<id>/`
- `/api/markets/system-summary/`

## Environment configuration
1. Copy the backend env file:
   ```bash
   cp apps/backend/.env.example apps/backend/.env
   ```
2. Adjust values if needed.

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
4. Start the backend server.
5. Open Django admin.
6. Inspect or query the read-only API.
7. Point the frontend at the backend and render live demo catalog data.

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

What gets created right now:
- 2 demo providers
- 6 demo events
- 12 demo markets
- 72 demo snapshots
- 6 demo market rules

The seed is update-or-create based, so it is reasonably safe to run more than once during local development.

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

Recommended admin checks after seeding:
- open **Providers** and verify counts per provider
- open **Events** and review category/status coverage
- open **Markets** and inspect status badges, liquidity, linked events, and snapshot counts
- open a market detail page and review rule inlines plus the latest snapshots inline
- open **Market Snapshots** to verify recent time-series values

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

## Settings layout
- `base.py` contains shared defaults, installed apps, middleware, DRF, CORS, PostgreSQL, Redis, and Celery defaults.
- `local.py` keeps local development behavior simple.
- `test.py` uses SQLite and eager Celery execution for lightweight test runs.
- `production.py` is reserved as a minimal production profile for later hardening.

By default, `manage.py`, ASGI, WSGI, and Celery use `config.settings.local` unless `DJANGO_SETTINGS_MODULE` is provided explicitly.

## Local frontend integration
CORS is configured for local Vite defaults only:
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:4173`
- `http://127.0.0.1:4173`

Adjust `DJANGO_CORS_ALLOWED_ORIGINS` if your local frontend runs elsewhere.

With the new market seed and read-only endpoints in place, the frontend can now start rendering:
- provider catalogs
- event groupings
- market list cards/tables
- detail pages with recent price history
- simple dashboard counts

## Celery readiness
Celery is wired through `config/celery.py` and autodiscovers tasks from installed apps.

Useful starter commands:

```bash
cd apps/backend
celery -A config worker -l info
celery -A config inspect ping
```

A minimal shared task exists in `apps.common.tasks.ping` as a wiring example only.

## Tests
Run backend tests with the dedicated test settings:

```bash
cd apps/backend
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
```

## What is intentionally not implemented yet
- Trading logic
- Provider integrations or sync jobs
- Authentication and authorization layers
- Orders, positions, fills, or paper trading workflows
- Signals, risk, or portfolio workflows
- Audit event persistence
- Background ingestion workflows beyond Celery wiring
- Machine learning or advanced dashboards

This backend is prepared for the next stage without adding premature business complexity.
