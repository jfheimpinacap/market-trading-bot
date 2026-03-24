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
│   ├── paper_trading/
│   └── proposal_engine/
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
- `apps.risk_demo`: demo-only trade guard layer that evaluates proposed paper trades with explainable heuristics before execution.
- `apps.signals`: demo-only signals and mock-agent layer that generates local insights from market snapshots and exposes read-only endpoints for the frontend.
- `apps.postmortem_demo`: demo-only trade review layer that generates post-trade reviews for executed paper trades using deterministic heuristics.
- `apps.agents`: placeholder app for future agent domain work.
- `apps.audit`: placeholder app for future audit and post-mortem work.
- `apps.policy_engine`: demo-only operational approval layer that translates trade context into `AUTO_APPROVE`, `APPROVAL_REQUIRED`, or `HARD_BLOCK`.
- `apps.proposal_engine`: demo-only trade proposal layer that consolidates market + signals + risk + policy + paper context into auditable `TradeProposal` records.
- `apps.semi_auto_demo`: conservative semi-autonomous demo orchestration layer for evaluate-only, guarded paper auto-execution, and pending manual approvals.

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


## Real market data (new, read-only)

The backend now supports **real market data ingestion in read-only mode** for:
- Kalshi
- Polymarket

Implemented boundaries:
- provider-agnostic adapter layer (`libs/provider-core`, `libs/provider-kalshi`, `libs/provider-polymarket`)
- manual ingestion commands:
  - `python manage.py ingest_kalshi_markets`
  - `python manage.py ingest_polymarket_markets`
- optional flags: `--limit`, `--active-only`, `--provider-market-id`, `--query`
- normalized persistence into existing `Provider`/`Event`/`Market` models plus basic `MarketSnapshot`
- explicit source separation: `source_type=demo` vs `source_type=real_read_only`

API filtering additions on `/api/markets/`:
- `provider`
- `status`
- `category`
- `active` / `is_active`
- `source_type`
- `is_demo`
- `is_real`
- `search`

Explicitly still out of scope:
- real trading auth
- order placement/execution
- real portfolio/positions
- websocket/polling auto-sync

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


## Paper trading on real-market data mode

The backend now supports **paper trading on real-market data** with strict boundary separation:

- **Market data source** can be `demo` or `real_read_only`.
- **Execution mode** remains `paper_demo_only` for all paper trades.
- Real markets are still read-only catalog data; no real auth, no real order placement, no real portfolio sync.

What is enabled now:
- `POST /api/paper/trades/` accepts `real_read_only` markets when they are paper-tradable.
- `POST /api/risk/assess-trade/`, `POST /api/policy/evaluate-trade/`, and `POST /api/proposals/generate/` work with real read-only markets.
- serializers expose explicit mode fields (`source_type`, `is_real_data`, `paper_tradable`, `execution_mode`) to avoid ambiguity.

Paper tradability guardrails:
- open + active market required
- paused/terminal market blocked
- missing valid yes/no/probability pricing blocked
- clear validation messages when blocked

Still out of scope:
- real execution/auth/order routing
- real balances/positions/portfolio
- websocket execution or continuous exchange sync

## Risk demo app summary
The `apps.risk_demo` app adds a first trade-guard boundary between market detail and paper trade execution without pretending to be a real risk engine.

Current risk demo model:
- `TradeRiskAssessment`

Current risk demo workflow:
- evaluate a proposed trade via `POST /api/risk/assess-trade/`
- persist recent assessments for admin and traceability
- reuse market status, paper account balances, open positions, liquidity, spread, activity, and demo signals as deterministic heuristics

Current risk demo endpoints:
- `/api/risk/assess-trade/`
- `/api/risk/assessments/`

Out of scope by design:
- real risk engine logic
- VaR / Kelly / auto-sizing
- broker or provider integrations
- automatic trade execution

## Policy engine demo app summary
The `apps.policy_engine` app adds the missing governance layer between analytical risk and paper trade execution.

Current policy engine model:
- `ApprovalDecision`

Current policy engine workflow:
- evaluate a proposed trade via `POST /api/policy/evaluate-trade/`
- persist the approval decision together with matched rules, rationale, recommendation, and linked risk/signal context
- translate `risk_demo` output into an operational decision instead of duplicating risk logic
- reuse paper account exposure, market operability, and automation thresholds as deterministic governance rules

Current policy engine endpoints:
- `/api/policy/evaluate-trade/`
- `/api/policy/decisions/`
- `/api/policy/summary/`

Operational decisions returned today:
- `AUTO_APPROVE`
- `APPROVAL_REQUIRED`
- `HARD_BLOCK`

Out of scope by design:
- multi-user approval queues
- autonomous execution
- ML-based policy scoring
- push notifications or realtime approval routing

## Proposal engine demo app summary
The `apps.proposal_engine` app consolidates demo market context, recent signals, risk guard output, policy decisions, and paper-account exposure into a single auditable proposal object for backend-first workflows.

Current proposal engine model:
- `TradeProposal`

Current proposal engine workflow:
- generate one proposal via `POST /api/proposals/generate/`
- compute direction (`BUY_YES`, `BUY_NO`, `HOLD`, `AVOID`) using clear local heuristics
- run `risk_demo` and `policy_engine` checks before persisting `is_actionable` and recommendation
- persist metadata linking signals, account context, and downstream assessment IDs

Current proposal engine endpoints:
- `/api/proposals/`
- `/api/proposals/<id>/`
- `/api/proposals/generate/`

Out of scope by design:
- frontend proposal UI
- auto-trading or batch autonomous generation
- real market data integrations
- ML/LLM decisioning
- complex approval queue orchestration



## Semi-auto demo app summary
The `apps.semi_auto_demo` app adds a conservative orchestration layer on top of proposal/risk/policy/paper-trading without duplicating policy logic.

Current semi-auto models:
- `SemiAutoRun`
- `PendingApproval`

Current semi-auto workflow:
- evaluate-only cycle that generates proposals and classifies outcomes without execution
- scan-and-execute cycle that only auto-executes strict `AUTO_APPROVE` + guardrail-compliant BUY paper proposals
- pending approval queue for `APPROVAL_REQUIRED`
- explicit block path for `HARD_BLOCK` and guardrail failures

Current semi-auto endpoints:
- `/api/semi-auto/evaluate/`
- `/api/semi-auto/run/`
- `/api/semi-auto/runs/`
- `/api/semi-auto/runs/<id>/`
- `/api/semi-auto/pending-approvals/`
- `/api/semi-auto/pending-approvals/<id>/approve/`
- `/api/semi-auto/pending-approvals/<id>/reject/`
- `/api/semi-auto/summary/`

Out of scope by design:
- real trading execution
- exchange auth
- autonomous background schedulers/workers
- websockets or complex concurrency

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


## Post-mortem demo app summary
The `apps.postmortem_demo` app closes the first local review loop across markets, signals, risk demo, paper trading, and the frontend `/postmortem` workspace.

Current post-mortem model:
- `TradeReview`

Current post-mortem workflow:
- generate or refresh trade reviews with `python manage.py generate_trade_reviews`
- classify each executed paper trade as `FAVORABLE`, `NEUTRAL`, or `UNFAVORABLE` using explainable heuristics
- persist summary, rationale, lesson, recommendation, estimated outcome context, and links back to the original trade
- expose read-only review endpoints for the frontend and admin

Current post-mortem endpoints:
- `/api/reviews/`
- `/api/reviews/<id>/`
- `/api/reviews/summary/`

Out of scope by design:
- ML-based post-mortem analysis
- autonomous post-trade agents
- news-based attribution
- real-time streaming review generation

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
- `APP_MODE`
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
python manage.py generate_trade_reviews
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
- `lite.py` enables lightweight local execution without Docker using SQLite.
- `test.py` uses SQLite and eager Celery execution for lightweight test runs.
- `production.py` is reserved as a minimal production profile for later hardening.

By default, `manage.py`, ASGI, WSGI, and Celery use `config.settings.local` unless `DJANGO_SETTINGS_MODULE` is provided explicitly.

### Full mode vs lite mode

- **Full mode:** `config.settings.local` (PostgreSQL + Redis, usually with Docker Compose).
- **Lite mode:** `config.settings.lite` (SQLite, Docker skipped, Redis optional/disabled).

Useful launcher commands:

```bash
python start.py --lite
python start.py setup --lite
python start.py up --lite
```

In lite mode, backend behavior stays local-first paper/demo only with reduced infra expectations.

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

## Automation demo

The backend now includes `apps/automation_demo/`, a local-first orchestration layer for explicit user-triggered demo actions.

### Available endpoints

- `POST /api/automation/simulate-tick/`
- `POST /api/automation/generate-signals/`
- `POST /api/automation/revalue-portfolio/`
- `POST /api/automation/generate-trade-reviews/`
- `POST /api/automation/sync-demo-state/`
- `POST /api/automation/run-demo-cycle/`
- `GET /api/automation/runs/`
- `GET /api/automation/runs/<id>/`
- `GET /api/automation/summary/`

### Intentional scope

This layer reuses the existing simulation, signals, paper trading, and post-mortem services. It records `DemoAutomationRun` rows for traceability, but it does **not** enable auto-trading, schedulers, Celery orchestration, provider integrations, or autonomous background agents.


## Continuous demo loop app summary
The `apps.continuous_demo` app adds a local-first autonomous loop for controlled background demo operation without real execution.

Current continuous demo models:
- `ContinuousDemoSession`
- `ContinuousDemoCycleRun`
- `LoopRuntimeControl`

Current continuous demo workflow:
- start/pause/resume/stop managed loop sessions
- run one manual cycle on demand
- one RUNNING session at a time with cycle-level concurrency guard
- strict paper-only path by reusing `automation_demo` + `semi_auto_demo` services
- pending approvals are delegated to `semi_auto_demo.PendingApproval`

Current continuous demo endpoints:
- `/api/continuous-demo/start/`
- `/api/continuous-demo/stop/`
- `/api/continuous-demo/pause/`
- `/api/continuous-demo/resume/`
- `/api/continuous-demo/run-cycle/`
- `/api/continuous-demo/status/`
- `/api/continuous-demo/sessions/`
- `/api/continuous-demo/sessions/<id>/`
- `/api/continuous-demo/cycles/`
- `/api/continuous-demo/cycles/<id>/`
- `/api/continuous-demo/summary/`

Out of scope by design:
- real trading execution
- exchange credentials/authentication
- distributed schedulers and websocket orchestration


## Safety hardening layer (paper/demo only)

- New `apps.safety_guard` module adds explicit guardrails for operational safety.
- Includes configurable limits for exposure, session drawdown, auto-trade caps, cooldown thresholds, and kill switch behavior.
- `continuous_demo` and `semi_auto_demo` now consult safety state before auto execution.
- Critical/manual actions remain manual by design: kill switch enable/disable, cooldown reset, config updates, pending approval decisions.


## Evaluation lab app summary
The `apps.evaluation_lab` app adds a benchmark/evaluation harness to objectively measure autonomous paper/demo behavior before increasing system autonomy.

Current evaluation models:
- `EvaluationRun`
- `EvaluationMetricSet`

Current evaluation workflow:
- build an auditable run from an existing continuous demo session (`POST /api/evaluation/build-for-session/<session_id>/`)
- aggregate cross-module metrics from cycles, proposals, approvals, paper trades, post-mortem reviews, safety events, and portfolio snapshots
- expose run summaries and simple comparisons for operator review

Current evaluation endpoints:
- `/api/evaluation/summary/`
- `/api/evaluation/runs/`
- `/api/evaluation/runs/<id>/`
- `/api/evaluation/recent/`
- `/api/evaluation/comparison/?left_id=<id>&right_id=<id>`

Out of scope by design:
- strategy optimization/tuning
- ML/LLM scoring
- real-money execution
