# Backend Django API

Backend base for the `market-trading-bot` monorepo. This service is intentionally local-first and currently focuses on clean project structure, a practical prediction-market catalog, and a smooth local workflow.

## Current purpose
- Provide a modular Django + DRF API base inside the monorepo.
- Keep a stable local development setup for PostgreSQL, Redis, Celery, and the frontend.
- Expose a lightweight healthcheck at `/api/health/`.
- Provide a provider-agnostic market domain for catalog, metadata, rule text, snapshot history, and local simulation work.
- Make it easy to seed realistic demo data locally for admin and frontend development.
- Make the demo dataset feel alive locally without real provider integrations, trading, or websockets.

## Internal structure

```text
apps/backend/
├── apps/
│   ├── agents/
│   ├── audit/
│   ├── common/
│   ├── health/
│   ├── markets/
│   └── paper_trading/
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
- `apps.markets`: provider, event, market, market snapshot, and market rule models plus demo seeding, simulation, admin tooling, and read-only API endpoints.
- `apps.paper_trading`: demo-only paper account, positions, trades, portfolio snapshots, valuation services, admin tooling, and basic write APIs for local investing flows.
- `apps.signals`: demo-only signals and mock-agent layer that generates local insights from market snapshots and exposes read-only endpoints for the frontend.
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

Current market workflows:
- deterministic demo seeding via `seed_markets_demo`
- live-looking local simulation via `simulate_markets_tick`
- optional local looping via `simulate_markets_loop`

Current read-only market endpoints:
- `/api/markets/providers/`
- `/api/markets/events/`
- `/api/markets/`
- `/api/markets/<id>/`
- `/api/markets/system-summary/`

## Paper trading app summary
The `apps.paper_trading` app provides the first backend base for demo investing with fictional money, using existing `Market` prices as the execution source of truth.

Current paper trading models:
- `PaperAccount`
- `PaperPosition`
- `PaperTrade`
- `PaperPortfolioSnapshot`

Current paper trading workflows:
- idempotent demo account seeding via `seed_paper_account`
- immediate demo trade execution via `POST /api/paper/trades/`
- mark-to-market refresh via `refresh_paper_portfolio` or `POST /api/paper/revalue/`
- account summary and exposure inspection via read endpoints and Django admin

Current paper trading endpoints:
- `/api/paper/account/`
- `/api/paper/positions/`
- `/api/paper/trades/`
- `/api/paper/summary/`
- `/api/paper/revalue/`
- `/api/paper/snapshots/`


## Signals app summary
The `apps.signals` app adds the first demo-only bridge between market simulation, paper trading, and future automation architecture.

Current signals models:
- `MockAgent`
- `MarketSignal`
- `SignalRun`

Current signals workflows:
- idempotent mock-agent seeding via `seed_mock_agents`
- local heuristic signal generation via `generate_demo_signals`
- read-only signal browsing for the frontend and admin

Current signals endpoints:
- `/api/signals/`
- `/api/signals/<id>/`
- `/api/signals/agents/`
- `/api/signals/summary/`

## Environment configuration
1. Copy the backend env file:
   ```bash
   cp apps/backend/.env.example apps/backend/.env
   ```
2. Adjust values if needed.

If you prefer the repo launcher, `python start.py setup` or `python start.py up` will create `apps/backend/.env` automatically when it is missing, using this template.

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
4. Run one or more simulation ticks, or start the loop mode.
5. Start the backend server.
6. Open Django admin.
7. Inspect the read-only API.
8. Refresh the frontend and verify the dashboard plus market pages react to changing values.

## Recommended shortcut from the repo root

The preferred local-first workflow for this repository is now:

```bash
python start.py
```

Or, if you only want to prepare the backend without keeping servers attached:

```bash
python start.py setup --skip-frontend
```

Backend-related launcher commands:

```bash
python start.py setup --skip-frontend
python start.py backend
python start.py seed
python start.py simulate-tick
python start.py simulate-loop
```

Paper trading setup and refresh commands:

```bash
cd apps/backend
python manage.py seed_paper_account
python manage.py refresh_paper_portfolio
```

What the launcher handles before running backend commands:

- creates `apps/backend/.env` from `apps/backend/.env.example` if needed
- creates `apps/backend/.venv` if it does not exist
- installs `requirements.txt` only when the dependency hash changes
- starts PostgreSQL and Redis unless `--skip-infra` is used
- runs `python manage.py migrate`
- auto-seeds the demo catalog during `up`, `setup`, and `backend` only when no markets exist yet
- starts the Django dev server in detached mode by default so the main launcher can return without opening extra consoles
- waits for `http://localhost:8000/api/health/` before reporting backend startup success
- stores launcher state so `python start.py down` can stop the backend later

Useful backend launcher variants:

```bash
python start.py backend
python start.py backend --separate-windows
python start.py backend --skip-infra
python start.py backend --skip-seed
```

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

Create the demo paper account after the market seed:

```bash
python manage.py seed_paper_account
```

What gets created right now:
- 2 demo providers
- 6 demo events
- 12 demo markets
- 72 demo snapshots
- 6 demo market rules

The seed is update-or-create based, so it is reasonably safe to run more than once during local development.

### Run the simulation tick
Apply one local simulation pass over the demo markets:

```bash
cd apps/backend
python manage.py simulate_markets_tick
```

Useful variants:

```bash
python manage.py simulate_markets_tick --dry-run
python manage.py simulate_markets_tick --limit 5
python manage.py simulate_markets_tick --seed 7
```

What the tick can change:
- `current_market_probability`
- `current_yes_price`
- `current_no_price`
- `liquidity`
- `volume_24h`
- `volume_total`
- `spread_bps`
- `status` in conservative scenarios
- fresh `MarketSnapshot` rows aligned with the updated market state

### Run the simulation loop
For a simple repeating local process:

```bash
cd apps/backend
python manage.py simulate_markets_loop --interval 10 --iterations 20
```

Continuous mode:

```bash
python manage.py simulate_markets_loop --interval 5
```

Stop continuous mode with `Ctrl+C`.

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

Recommended admin checks after seeding and simulation:
- open **Providers** and verify counts per provider
- open **Events** and review category/status coverage
- open **Markets** and inspect status badges, liquidity, snapshot counts, latest snapshot, and last simulation tick
- open a market detail page and review rule inlines plus the latest snapshots inline
- open **Market Snapshots** to verify recent time-series values and new simulated rows
- open **Paper Accounts** and confirm the demo account cash/equity fields update after trades
- open **Paper Positions** to inspect side, quantity, mark price, and unrealized PnL per market
- open **Paper Trades** to verify buy/sell history and linked market navigation
- open **Paper Portfolio Snapshots** to confirm account-level history is being captured

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

Suggested simulation verification:

```bash
curl http://localhost:8000/api/markets/system-summary/
python manage.py simulate_markets_tick
curl http://localhost:8000/api/markets/system-summary/
```

The second summary response should report a higher `total_snapshots` count after a live tick.

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

## Simulation design choices
The simulation layer is intentionally conservative:
- only demo markets are eligible
- resolved/cancelled/archived markets are skipped
- open markets move the most
- paused markets mostly drift slightly and may occasionally reopen
- closed markets are nearly static and only move toward resolution states
- probabilities are clamped between `0.0100` and `0.9900`
- prices are derived from probability rather than simulated independently
- `volume_total` only increases
- the API stays unchanged so the existing frontend sees changes via refresh alone

This keeps the system maintainable and ready for later additions like a system page, launcher, signals, mock agents, and paper-trading layers.

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

Set `VITE_API_BASE_URL` in the frontend to the backend URL, typically `http://localhost:8000/api`.

## Testing
Run backend market tests with the dedicated test settings:

```bash
cd apps/backend
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps.markets
```

## What is intentionally not implemented yet
This stage does **not** add:
- real Kalshi or Polymarket integrations
- trading execution
- paper trading workflows
- orders, fills, positions, or portfolio state
- Celery-based sync pipelines
- websockets
- signals or agent workflows
- ML, forecasting, or advanced analytics dashboards
