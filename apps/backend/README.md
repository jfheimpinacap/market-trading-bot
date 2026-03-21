# Backend Django API

Backend base for the `market-trading-bot` monorepo. This service is intentionally local-first and currently focuses on clean project structure, environment-driven configuration, and reusable backend foundations rather than trading logic.

## Current purpose
- Provide a modular Django + DRF API base inside the monorepo.
- Keep a stable local development setup for PostgreSQL, Redis, Celery, and the frontend.
- Expose a lightweight healthcheck at `/api/health/`.
- Provide an initial provider-agnostic market domain for catalog, metadata, and snapshot history work.
- Leave other domain apps intentionally small until their scope is ready.

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
- `apps.markets`: provider, event, market, market snapshot, and market rule domain models plus basic read-only API endpoints.
- `apps.agents`: placeholder app for future agent domain work.
- `apps.audit`: placeholder app for future audit and post-mortem work.

## Markets app summary
The `apps.markets` app now provides the initial database foundation for prediction-market data without adding trading workflows or provider integrations.

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

Use Django admin to inspect this data locally once migrated.

## Settings layout
- `base.py` contains shared defaults, installed apps, middleware, DRF, CORS, PostgreSQL, Redis, and Celery defaults.
- `local.py` keeps local development behavior simple.
- `test.py` uses SQLite and eager Celery execution for lightweight test runs.
- `production.py` is reserved as a minimal production profile for later hardening.

By default, `manage.py`, ASGI, WSGI, and Celery use `config.settings.local` unless `DJANGO_SETTINGS_MODULE` is provided explicitly.

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

## Database and migrations
The default runtime database is PostgreSQL configured via environment variables.

Run migrations from `apps/backend`:

```bash
cd apps/backend
python manage.py migrate
```

If you are working on the market domain and need to generate a new migration after modifying models:

```bash
cd apps/backend
python manage.py makemigrations markets
```

## Run the development server

```bash
cd apps/backend
python manage.py runserver
```

The API will be available on `http://localhost:8000/`.

## API examples
Healthcheck:

```bash
curl http://localhost:8000/api/health/
```

Markets endpoints:

```bash
curl http://localhost:8000/api/markets/providers/
curl http://localhost:8000/api/markets/
curl http://localhost:8000/api/markets/events/
curl http://localhost:8000/api/markets/1/
```

## DRF conventions for future work
- Keep routes grouped per app in each app's own `urls.py`.
- Mount app routes centrally from `config/api.py` under `/api/`.
- Keep `views.py` for endpoint classes/functions and `serializers.py` for request/response shaping.
- Prefer simple serializers and service extraction over custom internal frameworks.
- Grow domain apps incrementally instead of introducing internal abstraction layers early.

## Local frontend integration
CORS is configured for local Vite defaults only:
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:4173`
- `http://127.0.0.1:4173`

Adjust `DJANGO_CORS_ALLOWED_ORIGINS` if your local frontend runs elsewhere.

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
- Background workflows beyond Celery wiring

This backend is prepared for future stages without adding premature business complexity.
