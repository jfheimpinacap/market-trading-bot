# Backend Django API

Backend base for the `market-trading-bot` monorepo. This service is intentionally local-first and currently focuses on clean project structure, environment-driven configuration, and reusable backend foundations rather than trading logic.

## Current purpose
- Provide a modular Django + DRF API base inside the monorepo.
- Keep a stable local development setup for PostgreSQL, Redis, Celery, and the frontend.
- Expose a lightweight healthcheck at `/api/health/`.
- Leave serious but intentionally empty domain apps ready for future iterations.

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
- `apps.markets`: placeholder app for future market domain work.
- `apps.agents`: placeholder app for future agent domain work.
- `apps.audit`: placeholder app for future audit and post-mortem work.

## Settings layout
- `config/settings/base.py`: shared settings, installed apps, middleware, DRF, CORS, PostgreSQL, Redis, and Celery defaults.
- `config/settings/local.py`: local development defaults.
- `config/settings/test.py`: lightweight SQLite-backed test configuration.
- `config/settings/production.py`: reserved minimal production profile for later hardening.

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

## Run the development server

```bash
cd apps/backend
python manage.py runserver
```

The API will be available on `http://localhost:8000/`.

## Healthcheck
Test the health endpoint:

```bash
curl http://localhost:8000/api/health/
```

Expected JSON shape:

```json
{
  "status": "ok",
  "service": "market-trading-bot-backend",
  "environment": "local",
  "database_configured": true,
  "redis_configured": true
}
```

## DRF conventions for future work
- Keep routes grouped per app in each app's own `urls.py`.
- Mount app routes centrally from `config/api.py` under `/api/`.
- Keep `views.py` for endpoint classes/functions and `serializers.py` for request/response shaping.
- Add domain models only when the business scope for that app is ready.
- Prefer simple serializers and service extraction over custom internal frameworks.

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
- Provider integrations
- Authentication and authorization layers
- Market/order/position models
- Risk, signals, or paper trading workflows
- Audit event persistence
- Background workflows beyond Celery wiring

This backend is now prepared for those future stages without adding premature business complexity.
