# Backend Django API

Backend base for the `market-trading-bot` monorepo. This service is intentionally local-first and currently focuses on clean project structure, a practical prediction-market catalog, and a smooth local workflow.

## Current purpose
- Provide a modular Django + DRF API base inside the monorepo.
- Keep a stable local development setup for PostgreSQL, Redis, Celery, and the frontend.
- Expose a lightweight healthcheck at `/api/health/`.
- Provide a provider-agnostic market domain for catalog, metadata, rule text, snapshot history, and local simulation work.
- Make it easy to seed realistic demo data locally for admin and frontend development.
- Make the demo dataset feel alive locally without real provider integrations, trading, or websockets.
- Provide precedent-aware agent support via `memory_retrieval` with conservative and auditable influence on research/prediction/risk/signals/postmortem.

## Precedent-aware backend layer (new)

- Added `AgentPrecedentUse` for auditable agent-memory usage records.
- Added `memory_retrieval/services/assist.py` and `memory_retrieval/services/influence.py` to separate:
  - retrieval
  - precedent summary
  - influence suggestion
  - usage persistence
- New audit endpoints:
  - `GET /api/memory/precedent-uses/`
  - `GET /api/memory/precedent-uses/<id>/`
  - `GET /api/memory/influence-summary/`
- Existing assist endpoints for research/prediction/risk/postmortem now return influence metadata + summary (not only run IDs).
- Mission control can optionally refresh memory index on cadence (`run_memory_index_refresh_every_n_cycles`) and cycle details now mark precedent-aware mode.

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
- `apps.signals`: demo-only signals + formal signal-fusion layer that consolidates research/prediction/risk into ranked opportunity board outputs and proposal gating.
- `apps.postmortem_demo`: demo-only trade review layer that generates post-trade reviews for executed paper trades using deterministic heuristics.
- `apps.agents`: placeholder app for future agent domain work.
- `apps.audit`: placeholder app for future audit and post-mortem work.
- `apps.policy_engine`: demo-only operational approval layer that translates trade context into `AUTO_APPROVE`, `APPROVAL_REQUIRED`, or `HARD_BLOCK`.
- `apps.proposal_engine`: demo-only trade proposal layer that consolidates market + signals + risk + policy + paper context into auditable `TradeProposal` records.
- `apps.semi_auto_demo`: conservative semi-autonomous demo orchestration layer for evaluate-only, guarded paper auto-execution, and pending manual approvals.
- `apps.experiment_lab`: strategy profile persistence plus experiment run orchestration across replay and evaluation, with normalized comparison outputs.
- `apps.prediction_training`: offline prediction dataset/training/model-registry plus model governance (heuristic-vs-artifact comparison + recommendation).
- `apps.research_agent`: narrative scan/research layer with RSS + Reddit + optional X/Twitter adapter ingestion, local LLM structured analysis, social normalization, heuristic market linking, and shortlist candidate generation for paper/demo workflows.
- `apps.position_manager`: position lifecycle manager / exit decision engine that governs open paper positions with HOLD/REDUCE/CLOSE/REVIEW_REQUIRED decisions and auditable exit plans.

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

## Position lifecycle manager summary
The `apps.position_manager` app closes the paper lifecycle loop after entry:

- consumes open paper positions + latest risk watch events + prediction/research drift context
- emits explicit lifecycle decisions per position (`HOLD`, `REDUCE`, `CLOSE`, `REVIEW_REQUIRED`, `BLOCK_ADD`)
- produces one `PositionExitPlan` per decision with queue/auto-execute path and final recommended action
- honors runtime and safety authority before any paper close/reduce action
- routes constrained actions into operator queue for review

Endpoints:
- `/api/positions/run-lifecycle/`
- `/api/positions/lifecycle-runs/`
- `/api/positions/lifecycle-runs/<id>/`
- `/api/positions/decisions/`
- `/api/positions/summary/`

Explicit non-goals remain:
- no real-money execution
- no real exchange orders/stops
- no opaque planner/LLM as final authority
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

## Learning memory / adaptive heuristics demo app (new)

Se agregó `apps.learning_memory` como capa explícita de memoria operativa demo.

Incluye:
- modelos auditables `LearningMemoryEntry` y `LearningAdjustment`
- servicios de ingesta heurística desde postmortem/evaluation/safety
- rebuild deterministico vía command y endpoint
- API read-first para memory/adjustments/summary
- integración conservadora con `proposal_engine` y `risk_demo`

Comandos y endpoints clave:
- `python manage.py rebuild_learning_memory`
- `GET /api/learning/memory/`
- `GET /api/learning/adjustments/`
- `GET /api/learning/summary/`
- `POST /api/learning/rebuild/`


## Controlled learning loop integration (new)

Se integró `learning_memory` con `automation_demo` y `continuous_demo` sin rehacer arquitectura:

- `LearningRebuildRun` persiste cada rebuild con trazabilidad y métricas.
- `/api/automation/` incluye:
  - `POST /rebuild-learning-memory/`
  - `POST /run-full-learning-cycle/`
- `/api/learning/` incluye:
  - `GET /rebuild-runs/`
  - `GET /rebuild-runs/<id>/`
  - `GET /integration-status/`
- `continuous_demo` agrega settings conservadores para rebuild (`learning_rebuild_enabled`, `learning_rebuild_every_n_cycles`, `learning_rebuild_after_reviews`), desactivado por defecto.

Jerarquía operativa explícita:
- learning ajusta (heurístico, acotado)
- policy gobierna decisiones
- safety limita/puede frenar

Fuera de alcance: ML real, LLM local, ejecución real o dinero real.

## Real data refresh pipeline hardening (new)

A dedicated backend boundary now exists at `apps.real_data_sync` for hardened read-only provider refresh runs.

What it adds:
- persisted `ProviderSyncRun` audit model (`SUCCESS/PARTIAL/FAILED/RUNNING`)
- sync orchestration service that reuses existing provider adapters + normalization (`apps.markets.services.real_data_ingestion`)
- provider health/status view (`last_success`, `last_failed`, `consecutive_failures`, stale warning)
- API endpoints:
  - `POST /api/real-sync/run/`
  - `GET /api/real-sync/runs/`
  - `GET /api/real-sync/runs/<id>/`
  - `GET /api/real-sync/status/`
  - `GET /api/real-sync/summary/`
- management command:
  - `python manage.py sync_real_markets --provider kalshi`
  - `python manage.py sync_real_markets --provider polymarket --active-only --limit 100`
  - `python manage.py sync_real_markets --provider kalshi --market-id <id>`

Scope remains intentionally strict:
- read-only market-data refresh only
- no real exchange auth
- no real order execution
- no websocket/streaming sync


## Real-market autonomous paper scope
`apps.real_market_ops` introduces a conservative autonomous operation scope:
- source must remain `real_read_only`
- execution remains `paper_demo_only`
- stale/degraded provider status can hard-block eligibility
- insufficient pricing/liquidity/volume excludes markets
- every run is persisted as `RealMarketOperationRun` for auditability.

### API
- `POST /api/real-ops/evaluate/`
- `POST /api/real-ops/run/`
- `GET /api/real-ops/runs/`
- `GET /api/real-ops/runs/<id>/`
- `GET /api/real-ops/status/`
- `GET /api/real-ops/eligible-markets/` (supporting endpoint)

## Allocation engine demo (new)

Nuevo módulo `apps.allocation_engine` para priorización y reparto de capital paper a nivel portfolio.

Qué hace:
- toma propuestas ya generadas por `proposal_engine` (sin duplicar risk/policy/safety)
- rankea candidatos con heurísticas auditable (score/confidence/risk/policy/exposición/provider/learning)
- asigna `final_allocated_quantity` conservadora con límites por cash, corrida y mercado
- persiste `AllocationRun` + `AllocationDecision`

Integración:
- `semi_auto_demo` y `real_market_ops` pasan por allocation antes de autoejecutar paper trades
- mantiene ejecución `paper_demo_only`

Fuera de alcance:
- optimización cuantitativa avanzada, Kelly, ML/LLM, dinero real

## Operator queue app (new)

`apps.operator_queue` introduces a centralized manual exception inbox:
- `OperatorQueueItem`: approval/escalation items with source, type, priority, linked proposal/market/pending approval/trade.
- `OperatorDecisionLog`: auditable manual decisions (`APPROVE`, `REJECT`, `SNOOZE`, etc.).

Endpoints:
- `GET /api/operator-queue/`
- `GET /api/operator-queue/<id>/`
- `GET /api/operator-queue/summary/`
- `POST /api/operator-queue/<id>/approve/`
- `POST /api/operator-queue/<id>/reject/`
- `POST /api/operator-queue/<id>/snooze/`
- `POST /api/operator-queue/rebuild/`

Integration notes:
- semi-auto and real-ops now create queue items when they create `PendingApproval`.
- approving a queue item executes paper trade when executable context exists (directly or via linked `PendingApproval`).
- execution remains paper/demo only; no real order path is introduced.

## Replay lab (historical replay / backtest-like demo)

Nuevo app: `apps.replay_lab`.

Qué hace:
- Ejecuta replay histórico sobre `MarketSnapshot` persistidos (sin APIs externas en runtime).
- Recorre timeline cronológico por pasos (`ReplayStep`) y guarda corrida (`ReplayRun`).
- Reutiliza proposal/risk/policy/allocation/safety para decisiones, pero siempre en paper/demo only.
- Aísla portfolio con una cuenta paper dedicada por run (`replay-run-<id>`), evitando contaminar la cuenta operativa principal.

Endpoints:
- `POST /api/replay/run/`
- `GET /api/replay/runs/`
- `GET /api/replay/runs/<id>/`
- `GET /api/replay/summary/`
- `GET /api/replay/runs/<id>/steps/`

Límites intencionales:
- No execution real
- No slippage/order-book sofisticado
- No backtesting cuantitativo institucional
- No ML/LLM


## Experiment lab summary
The `apps.experiment_lab` app adds a clear experimentation boundary without duplicating replay/evaluation engines.

Models:
- `StrategyProfile`: persisted operational profile (type, market scope, config JSON)
- `ExperimentRun`: auditable run record linked to strategy profile and optional replay/evaluation/session entities

Services:
- `services/profiles.py`: base profile seed set (`Conservative`, `Balanced`, `Aggressive-light`, etc.)
- `services/runner.py`: applies profile config and orchestrates replay/evaluation calls
- `services/comparison.py`: run-vs-run metric deltas and simple interpretation text

Endpoints:
- `GET /api/experiments/profiles/`
- `GET /api/experiments/profiles/<id>/`
- `POST /api/experiments/run/`
- `GET /api/experiments/runs/`
- `GET /api/experiments/runs/<id>/`
- `GET /api/experiments/comparison/?left_run_id=<id>&right_run_id=<id>`
- `POST /api/experiments/seed-profiles/`
- `GET /api/experiments/summary/`

Out of scope remains unchanged: no real execution, no real money, no auto-tuning optimizer, no ML/LLM strategy training.

## Readiness lab app summary (new)

`apps.readiness_lab` adds an auditable promotion-gate layer above evaluation/replay/experiments:

- `ReadinessProfile`: configurable gate thresholds (conservative/balanced/strict/custom)
- `ReadinessAssessmentRun`: persisted readiness decisions (`READY`, `CAUTION`, `NOT_READY`)
- services split:
  - `services/assessment.py`: metrics aggregation + final decision
  - `services/gates.py`: reusable gate evaluation rules
  - `services/recommendations.py`: deterministic recommendation generation
  - `services/profiles.py`: base profile seeding

Main endpoints:
- `GET /api/readiness/profiles/`
- `GET /api/readiness/profiles/<id>/`
- `POST /api/readiness/assess/`
- `GET /api/readiness/runs/`
- `GET /api/readiness/runs/<id>/`
- `GET /api/readiness/summary/`
- `POST /api/readiness/seed-profiles/`

Boundary remains strict: readiness does not trigger real trading or automatic promotion.

## Runtime governor app (new)

`apps.runtime_governor` introduces explicit operational mode governance for runtime autonomy.

Key models:
- `RuntimeModeProfile`: capability profile for each runtime mode
- `RuntimeModeState`: persisted effective runtime mode and operational status
- `RuntimeTransitionLog`: audit log of mode transitions and degradations

Key endpoints:
- `GET /api/runtime/status/`
- `GET /api/runtime/modes/`
- `POST /api/runtime/set-mode/`
- `GET /api/runtime/transitions/`
- `GET /api/runtime/capabilities/`

Governance rules include:
- readiness-aware promotion limits (`NOT_READY` and `CAUTION` constraints)
- safety-forced degradation (`kill switch`, `hard stop`, cooldown/pause restrictions)
- conservative fallback to safer modes when constraints are violated

Integration:
- `semi_auto_demo`, `continuous_demo`, and `real_market_ops` now reconcile runtime mode before execution and respect runtime capabilities.
- everything remains paper/demo only.

## Operator alerts app (`apps.operator_alerts`)

A new backend boundary provides a local-first incident center for operator attention management.

### Models
- `OperatorAlert`: persistent, deduplicated operational alert records.
- `OperatorDigest`: persisted summary windows for recent activity.

### Services
- `services/alerts.py`: emit + dedupe + acknowledge + resolve + summary.
- `services/aggregation.py`: lightweight integration rules across queue/safety/runtime/sync/readiness/continuous-demo.
- `services/digest.py`: build digest snapshots from a chosen time window.

### Endpoints
- `GET /api/alerts/`
- `GET /api/alerts/<id>/`
- `GET /api/alerts/summary/`
- `POST /api/alerts/<id>/acknowledge/`
- `POST /api/alerts/<id>/resolve/`
- `GET /api/alerts/digests/`
- `GET /api/alerts/digests/<id>/`
- `POST /api/alerts/build-digest/`
- `POST /api/alerts/rebuild/`

### Scope and boundary
This layer is paper/demo only and focused on auditable exception handling. It intentionally excludes external push channels, enterprise workflow orchestration, and real execution controls.

## Notification center (delivery + escalation routing)

Nuevo módulo `apps.notification_center` para sacar alertas/digests del panel con reglas claras y trazabilidad:

- `NotificationChannel`: catálogo de canales configurables (`ui_only`, `webhook`, `email`; extensible a slack/telegram/discord sin activarlos todavía).
- `NotificationRule`: matching explícito (`match_criteria`), `delivery_mode` (`immediate`/`digest`), `severity_threshold`, `cooldown_seconds`, `dedupe_window_seconds`, canales target.
- `NotificationDelivery`: bitácora persistida por intento (`SENT`, `FAILED`, `SUPPRESSED`, etc.) con `reason`, payload resumido y metadata de respuesta.

Servicios (`apps/notification_center/services/`):
- `routing.py`: evaluación de reglas, canales y supresión por dedupe/cooldown.
- `delivery.py`: construcción de payload, dispatch por canal, registro de delivery.
- `channels.py`: bootstrap de canal `ui_only`.
- `summary.py`: salud y métricas de delivery.

Integración:
- `operator_alerts` sigue siendo SoT de incidentes.
- `notification_center` solo decide si/cuándo/cómo notificar.
- digests existentes (`OperatorDigest`) ahora pueden entregarse por `send-digest`.

## Notification automation layer (new)

`apps.notification_center` was extended with a small automation layer:

- `NotificationAutomationState`: global/local toggles and cadence limits
- `NotificationEscalationEvent`: auditable escalation reason log
- automatic alert dispatch hooks from `operator_alerts.emit_alert`
- digest automation via local cycle windows (`run_digest_cycle`)
- escalation cycle for persistent incidents (`run_escalation_cycle`)

New API endpoints:
- `GET /api/notifications/automation-status/`
- `POST /api/notifications/automation-enable/`
- `POST /api/notifications/automation-disable/`
- `POST /api/notifications/run-automatic-dispatch/`
- `POST /api/notifications/run-digest-cycle/`
- `GET /api/notifications/escalations/`

Design boundary: still local-first, paper/demo only, no real execution, no distributed orchestration.

## Local LLM integration (`apps.llm_local`, new)

A new backend app provides a clean local LLM boundary for Ollama:

- `clients/ollama.py`: reusable local chat client with timeout/error handling
- `clients/embeddings.py`: reusable embedding client (`nomic-embed-text` by default)
- `prompts/`: centralized prompt templates (`proposal.py`, `postmortem.py`, `learning.py`)
- `schemas.py`: structured JSON validation for thesis/insights/learning note payloads
- `services/`: task-level orchestration (`proposal_text`, `postmortem_text`, `learning_text`, `embeddings`, `status`)
- `views.py`: thin API layer with clean degradation (`503` + `degraded=true`)

Endpoints:
- `GET /api/llm/status/`
- `POST /api/llm/proposal-thesis/`
- `POST /api/llm/postmortem-summary/`
- `POST /api/llm/learning-note/`
- `POST /api/llm/embed/`

Environment variables:
- `LLM_ENABLED=true|false`
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_CHAT_MODEL=<model>`
- `OLLAMA_EMBED_MODEL=nomic-embed-text`
- `OLLAMA_TIMEOUT_SECONDS=30`

Important scope boundary:
- LLM enriches text and explanations only.
- Risk/policy/safety remain deterministic authorities.
- No real execution path is introduced.

## Research agent MVP (RSS-first narrative scan)

New app: `apps.research_agent`

Main entities:
- `NarrativeSource`
- `NarrativeItem`
- `NarrativeAnalysis`
- `MarketNarrativeLink`
- `ResearchCandidate`
- `ResearchScanRun`

Service split:
- `services/ingest.py`: RSS ingestion + dedupe persistence
- `services/analyze.py`: structured narrative extraction via local LLM + heuristic fallback
- `services/linking.py`: basic heuristic narrative-to-market linking
- `services/shortlist.py`: candidate scoring/ranking
- `services/scan.py`: orchestrated run with audit trace

API endpoints:
- `GET/POST /api/research/sources/`
- `POST /api/research/run-ingest/`
- `POST /api/research/run-analysis/`
- `GET /api/research/items/`
- `GET /api/research/items/<id>/`
- `GET /api/research/candidates/`
- `GET /api/research/summary/`

Boundary: paper/demo research support only; no real execution path.

## Prediction agent MVP (new)

Nueva app: `apps.prediction_agent`.

Responsabilidades:
- feature building auditable (`services/features.py`)
- profile registry (`services/profiles.py`)
- scoring + edge (`services/scoring.py`)
- calibración básica (`services/calibration.py`)

Modelos principales:
- `PredictionModelProfile`
- `PredictionRun`
- `PredictionFeatureSnapshot`
- `PredictionScore`
- `PredictionOutcomeLabel` (base para labels futuros)

Endpoints:
- `GET /api/prediction/profiles/`
- `POST /api/prediction/score-market/`
- `GET /api/prediction/scores/`
- `GET /api/prediction/scores/<id>/`
- `GET /api/prediction/summary/`
- `POST /api/prediction/build-features/`

Integración:
- `research_agent` aporta señales narrativas agregadas
- `learning_memory` aporta nudges conservadores
- `proposal_engine` consume el último score como contexto adicional (metadata + thesis/rationale)

Boundary:
- paper/demo only
- no ejecución real
- no XGBoost entrenado todavía (solo contrato y placeholder de perfil)

## Prediction training pipeline (new)

A new `apps.prediction_training` module provides an offline-first trained-model foundation without changing governance boundaries:

- dataset construction from historical `MarketSnapshot` rows
- initial label: `future_probability_up_24h` (binary direction at +24h horizon)
- reproducible train/validation split and persisted training runs
- XGBoost model training + explicit sigmoid calibration
- model artifact registry with active model switching
- prediction runtime fallback to heuristic scorer whenever no active trained model exists or inference fails

This remains paper/demo only and does not replace `risk_demo`, `policy_engine`, or `safety_guard`.

## Agents orchestration app (`apps.agents`)

`apps.agents` is now the explicit orchestration boundary for local-first, paper/demo-only agent workflows.

### Data model
- `AgentDefinition`: registry for enabled/disabled agents and schema versions
- `AgentRun`: per-agent execution trace
- `AgentPipelineRun`: end-to-end pipeline execution trace
- `AgentHandoff`: structured transfer record between agent runs

### Services
- `services/registry.py`: default agent registration bootstrap
- `services/orchestrator.py`: controlled pipeline runner + run lifecycle
- `services/pipelines.py`: pipeline implementations reusing existing domain services
- `services/handoffs.py`: handoff creation helper

### API
- `GET /api/agents/`
- `GET /api/agents/runs/`
- `GET /api/agents/runs/<id>/`
- `POST /api/agents/run-pipeline/`
- `GET /api/agents/pipelines/`
- `GET /api/agents/pipelines/<id>/`
- `GET /api/agents/handoffs/`
- `GET /api/agents/summary/`

### Current pipeline integration
- `research_to_prediction`: uses `research_agent` candidate outputs and `prediction_agent` scoring
- `postmortem_to_learning`: uses `postmortem_demo` review generation and `learning_memory` rebuild
- `real_market_agent_cycle`: uses read-only real markets through research → prediction → risk (paper/demo assessments only)

### Explicit scope guardrails
- no real money
- no real execution
- no opaque planner
- no autonomous black-box agent authority


## Risk agent refinement (paper/demo only)
- New `apps/backend/apps/risk_agent/` module introduces structured `RiskAssessment`, `RiskSizingDecision`, `PositionWatchRun`, and `PositionWatchEvent`.
- Separation of concerns is explicit: prediction estimates; risk evaluates/sizes; policy authorizes; safety limits; runtime governs mode.
- API endpoints: `POST /api/risk-agent/assess/`, `POST /api/risk-agent/size/`, `POST /api/risk-agent/run-watch/`, `GET /api/risk-agent/assessments/`, `GET /api/risk-agent/watch-events/`, `GET /api/risk-agent/summary/`.
- Frontend route `/risk-agent` provides assessment, sizing, watch loop, and audit history panels.
- Out of scope remains unchanged: no real money, no real execution, no production-grade Kelly optimizer, no exchange stop-loss automation.

## Postmortem board committee (new)

`apps.postmortem_agents` adds a structured, auditable multi-perspective postmortem layer on top of existing `postmortem_demo` reviews.

Perspectives in v1:
- narrative/research
- prediction
- risk/sizing
- runtime/safety/operator context
- learning synthesis

Key entities:
- `PostmortemBoardRun`
- `PostmortemAgentReview`
- `PostmortemBoardConclusion`

Backend endpoints:
- `POST /api/postmortem-board/run/`
- `GET /api/postmortem-board/runs/`
- `GET /api/postmortem-board/runs/<id>/`
- `GET /api/postmortem-board/reviews/`
- `GET /api/postmortem-board/conclusions/`
- `GET /api/postmortem-board/summary/`

LLM-local usage is optional and bounded: reviewers always start from structured context and degrade gracefully when Ollama is unavailable.

## Research universe scanner / triage board (new)

`apps.research_agent` now separates three backend responsibilities:

- `services/universe_scan.py`: explicit universe run orchestration + persisted run stats.
- `services/market_triage.py`: transparent eligibility/triage rules and profile thresholds.
- `services/pursuit_board.py`: board summary + pursuit candidate query surface.

New core entities:
- `MarketUniverseScanRun`
- `MarketTriageDecision`
- `PursuitCandidate`

New endpoints:
- `POST /api/research/run-universe-scan/`
- `GET /api/research/universe-scans/`
- `GET /api/research/universe-scans/<id>/`
- `GET /api/research/pursuit-candidates/`
- `GET /api/research/board-summary/`
- `POST /api/research/run-triage-to-prediction/`

Design boundary: no real-money paths and no real order execution are introduced.


## Signal fusion agent / opportunity board

The backend now adds a formal fusion boundary (`apps.signals`) that *reuses* research, prediction, and risk outputs instead of replacing them.

Flow:
- research triage/pursuit candidate -> prediction score -> risk assessment/sizing -> signal fusion -> proposal gate

Key properties:
- transparent weighted fusion with explicit profiles
- auditable status assignment (`WATCH`, `CANDIDATE`, `PROPOSAL_READY`, `BLOCKED`)
- explicit proposal gating before `proposal_engine`
- paper/demo-only invariants preserved (no real execution path added)

## Opportunity supervisor app (new)

`apps.opportunity_supervisor` introduces a formal supervisor boundary for scan-to-proposal-to-execution-path orchestration in paper/demo mode.

Main persisted entities:
- `OpportunityCycleRun`
- `OpportunityCycleItem`
- `OpportunityExecutionPlan`

Main API endpoints:
- `POST /api/opportunities/run-cycle/`
- `GET /api/opportunities/cycles/`
- `GET /api/opportunities/cycles/<id>/`
- `GET /api/opportunities/items/`
- `GET /api/opportunities/summary/`

Governance authority remains unchanged:
- runtime governor still controls auto-execution capabilities
- policy engine still controls approval class
- safety guard still controls overrides/blocking

No real execution was added.

## Mission control app (new)

`apps.mission_control` adds a transparent autonomous operations control plane on top of existing modules.

What it adds:
- `MissionControlState`, `MissionControlSession`, `MissionControlCycle`, `MissionControlStep`
- service boundaries:
  - `services/controller.py` for start/pause/resume/stop/status and loop threading
  - `services/cycle_runner.py` for explicit cycle sequencing and step audit records
  - `services/state.py` for singleton runtime state control
  - `services/profiles.py` for conservative cadence profiles
- API endpoints under `/api/mission-control/` for status, controls, sessions, cycles, and summary

What it does not add:
- real-money execution
- real exchange auth/order routing
- distributed enterprise scheduling

## Portfolio governor app summary

Nueva app `apps.portfolio_governor` para gobernanza agregada de cartera:

- Modelos:
  - `PortfolioExposureSnapshot`
  - `PortfolioThrottleDecision`
  - `PortfolioGovernanceRun`
- Servicios:
  - `services/exposure.py`
  - `services/regime.py`
  - `services/throttle.py`
  - `services/governance.py`
  - `services/profiles.py`
- Endpoints:
  - `POST /api/portfolio-governor/run-governance/`
  - `GET /api/portfolio-governor/runs/`
  - `GET /api/portfolio-governor/runs/<id>/`
  - `GET /api/portfolio-governor/exposure/`
  - `GET /api/portfolio-governor/throttle/`
  - `GET /api/portfolio-governor/summary/`

Diferencias de responsabilidades:
- `risk_agent`: riesgo/sizing por oportunidad/posición.
- `position_manager`: lifecycle por posición (hold/reduce/close/review).
- `portfolio_governor`: contexto agregado de cartera + gating/throttling de nuevas entradas.

Out of scope (todavía): real money, real execution, optimizer institucional, correlaciones de producción, hedging complejo.

## Profile manager (adaptive meta-governance)

New app: `apps.profile_manager`.

Purpose:
- aggregate runtime/safety/readiness + portfolio governor inputs
- classify operational regime
- recommend/apply module profile bundle in auditable form
- keep runtime/safety/readiness as top-level constraints

Key endpoints:
- `POST /api/profile-manager/run-governance/`
- `GET /api/profile-manager/runs/`
- `GET /api/profile-manager/runs/<id>/`
- `GET /api/profile-manager/current/`
- `GET /api/profile-manager/summary/`
- `POST /api/profile-manager/apply-decision/<id>/`

Scope remains strictly local-first, single-user, paper/demo only.

## Execution simulator
- New paper-only execution realism layer under `apps/backend/apps/execution_simulator` with explicit order lifecycle, attempts, and fills.
- Mission control, opportunity supervisor, and position manager can feed orders into this layer before portfolio impact is applied.

## Execution-aware replay / evaluation realism / readiness impact

The backend now integrates execution realism into historical and readiness workflows without enabling real execution.

- Replay (`/api/replay/run/`) accepts:
  - `execution_mode`: `naive` or `execution_aware`
  - `execution_profile`: `optimistic_paper`, `balanced_paper`, `conservative_paper`
- In `execution_aware` mode replay routes intent through `execution_simulator` order lifecycle (full/partial/no-fill, cancel/expire, slippage).
- Replay run `details` include `execution_impact_summary` (fill/no-fill/partial rates, slippage, execution-adjusted pnl, execution drag, realism score).
- Evaluation runs store `metadata.execution_adjusted_snapshot` so snapshots include execution realism impact.
- Experiment normalized metrics and comparison deltas now include execution-aware fields and naive-vs-aware drag where available.
- Readiness assessments include `details.execution_impact_summary` and apply a bounded execution realism penalty to avoid perfect-fill optimism.

Still out of scope: real money, exchange routing, institutional microstructure, and complex hedging.

## Champion-challenger app (new)

A new backend module `apps.champion_challenger` provides a clear shadow-benchmark boundary for paper/demo operation.

Core entities:
- `StackProfileBinding`: explicit stack snapshot (prediction model/profile + research/signal/opportunity/mission/portfolio profiles + execution profile + runtime constraints snapshot)
- `ChampionChallengerRun`: auditable run record for champion vs challenger
- `ShadowComparisonResult`: normalized side-by-side metrics and deltas

Service split:
- `services/bindings.py`: champion/challenger binding construction and champion selection
- `services/shadow_runner.py`: run shadow benchmark in isolated replay execution-aware mode
- `services/comparison.py`: consolidate benchmark metrics and deltas
- `services/recommendation.py`: recommendation code + reasons

API endpoints:
- `POST /api/champion-challenger/run/`
- `GET /api/champion-challenger/runs/`
- `GET /api/champion-challenger/runs/<id>/`
- `GET /api/champion-challenger/current-champion/`
- `GET /api/champion-challenger/summary/`
- `POST /api/champion-challenger/set-champion-binding/`

Integration notes:
- uses `prediction_training` active model registry as optional binding input
- uses `profile_manager` state/bindings for runtime-aware defaults
- can be triggered by `mission_control` every N cycles (`run_shadow_benchmark_every_n_cycles`)
- reuses execution-aware replay realism so comparison is not perfect-fill optimistic

Out of scope remains explicit: real-money execution, automatic champion promotion, opaque meta-controller.

## Semantic memory retrieval app (new)

`apps.memory_retrieval` introduces a formal semantic precedent layer for paper/demo workflows.

Responsibilities:
- index high-value documents from learning memory, postmortem board, trade reviews, replay, experiments, and lifecycle decisions
- create/update embeddings using existing local `llm_local` embedding service
- execute auditable precedent retrieval runs with persisted ranks and scores
- expose case-based summary (similar cases, caution signals, failure modes, lessons)

Design choices:
- local-first single-user operation
- no mandatory external vector DB
- no view-layer business logic (services split across documents/embeddings/indexing/retrieval/precedents)
- retrieval enriches decision context; it does not become final decision authority

## Promotion committee (new)

`apps.promotion_committee` introduces a formal stack-governance boundary above champion/challenger and readiness:

- `StackEvidenceSnapshot`: normalized evidence synthesis
- `PromotionReviewRun`: auditable recommendation run
- `PromotionDecisionLog`: recommendation/apply event trail

Services are intentionally split to keep logic out of views:
- `services/evidence.py`
- `services/recommendation.py`
- `services/review.py`
- `services/apply.py`
- `services/state.py`

API endpoints:
- `POST /api/promotion/run-review/`
- `GET /api/promotion/runs/`
- `GET /api/promotion/runs/<id>/`
- `GET /api/promotion/current-recommendation/`
- `GET /api/promotion/summary/`
- `POST /api/promotion/apply/<id>/`

Boundaries:
- paper/demo only
- manual-first
- no opaque auto-switching


## Rollout manager layer (new)

`apps.rollout_manager` adds the formal transition layer between committee recommendation and full promotion.

What it does:
- creates `StackRolloutPlan` records with champion/candidate bindings, mode, canary percentage, sampling rule, and guardrails
- starts and tracks `StackRolloutRun` lifecycle (`RUNNING`, `PAUSED`, `COMPLETED`, `ROLLED_BACK`, `FAILED`)
- evaluates explicit guardrails and persists `RolloutGuardrailEvent`
- emits auditable `RolloutDecision` recommendations
- applies explicit rollback to champion-only routing

API endpoints:
- `POST /api/rollout/create-plan/`
- `POST /api/rollout/start/<id>/`
- `POST /api/rollout/pause/<id>/`
- `POST /api/rollout/resume/<id>/`
- `POST /api/rollout/rollback/<id>/`
- `GET /api/rollout/runs/`
- `GET /api/rollout/runs/<id>/`
- `GET /api/rollout/current/`
- `GET /api/rollout/summary/`

Design boundary:
- `promotion_committee` still recommends
- `champion_challenger` still benchmarks
- `rollout_manager` executes gradual, reversible paper/demo transition

## Incident commander boundary (new)

New app: `apps/incident_commander`

Responsibilities:
- detect recurring operational incidents
- maintain incident lifecycle + action/recovery audit trail
- apply conservative degraded mode orchestration
- integrate with mission_control, rollout_manager, runtime_governor, safety_guard, operator_alerts, notification_center, and operator_queue

Key rule: runtime/safety remain higher authority; incident commander can only degrade conservatively, never bypass safety guardrails.

## Chaos lab / resilience validation (new)

A new backend app, `apps.chaos_lab`, adds a formal resilience-validation layer on top of existing runtime safety systems.

What it does:
- seeds a baseline catalog of controlled experiments
- runs fault injection in scoped/reversible mode
- triggers existing detection/mitigation flows from `incident_commander`
- records auditable observations + benchmark metrics
- cleans injected artifacts after each run to avoid persistent corruption

Key endpoints:
- `GET /api/chaos/experiments/`
- `POST /api/chaos/run/`
- `GET /api/chaos/runs/`
- `GET /api/chaos/runs/<id>/`
- `GET /api/chaos/benchmarks/`
- `GET /api/chaos/summary/`

Out of scope (unchanged): real money, real execution, unrestricted destructive chaos, cluster orchestration, opaque planner control.


## Operational certification board (paper-only)

New app: `apps.certification_board`.

Purpose:
- Consolidate evidence from readiness, chaos/resilience, incidents, champion-challenger, promotion, rollout, execution-aware evaluation, runtime/safety, portfolio governor and profile manager.
- Issue an auditable certification recommendation.
- Materialize an explicit paper-only `OperatingEnvelope`.

Key API endpoints:
- `POST /api/certification/run-review/`
- `GET /api/certification/runs/`
- `GET /api/certification/runs/<id>/`
- `GET /api/certification/current/`
- `GET /api/certification/summary/`
- `POST /api/certification/apply/<id>/` (optional manual safe apply)

Scope boundaries:
- manual-first and conservative
- no real money
- no real execution
- no opaque auto go-live


## Broker bridge sandbox layer (new)

`apps.broker_bridge` adds a dedicated real-execution-readiness boundary while preserving paper-only behavior.

Core entities:
- `BrokerOrderIntent`
- `BrokerBridgeValidation`
- `BrokerDryRun`

Core services:
- `services/intents.py`: build intents from internal sources
- `services/mapping.py`: map internal objects to broker-like fields/profiles
- `services/validation.py`: envelope/runtime/safety/incident guardrail checks
- `services/dry_run.py`: simulated broker routing response
- `services/readiness.py`: summary counters for operator UI

API:
- `POST /api/broker-bridge/create-intent/`
- `POST /api/broker-bridge/validate/<id>/`
- `POST /api/broker-bridge/dry-run/<id>/`
- `GET /api/broker-bridge/intents/`
- `GET /api/broker-bridge/intents/<id>/`
- `GET /api/broker-bridge/summary/`

Important boundary:
`broker_bridge` does not replace `execution_simulator`; it records what would be sent to a future broker adapter while execution remains paper-only.

## Go-live gate (rehearsal only)

A new backend app `apps/go_live_gate` adds the final pre-live rehearsal boundary **without enabling live execution**.

- API namespace: `/api/go-live/*`
- Core entities: `GoLiveChecklistRun`, `GoLiveApprovalRequest`, `GoLiveRehearsalRun`, `CapitalFirewallRule`
- Core behavior:
  - persisted pre-live checklist runs
  - manual approval requests (manual-first, never auto-applied)
  - final rehearsal run over an existing `BrokerOrderIntent`
  - explicit capital firewall that blocks all live transition paths

This layer sits above `broker_bridge`: it does not remap orders and does not send anything live.

## Execution venue app (new)

`apps.execution_venue` introduces the canonical broker/exchange-facing contract while keeping the existing paper-only boundary:

- `VenueOrderPayload`: stable external order schema mapped from `BrokerOrderIntent`
- `VenueOrderResponse`: normalized response envelope (`ACCEPTED`, `REJECTED`, `HOLD`, `REQUIRES_CONFIRMATION`, `UNSUPPORTED`, `INVALID_PAYLOAD`)
- `VenueCapabilityProfile`: adapter feature matrix + constraints, with `live_supported=false`
- `VenueParityRun`: auditable parity checks across broker bridge dry-run, execution simulator context, and sandbox adapter output

Default adapter is `NullSandboxVenueAdapter` (no real connectivity, no real order submission).

New endpoints:
- `GET /api/execution-venue/capabilities/`
- `POST /api/execution-venue/build-payload/<intent_id>/`
- `POST /api/execution-venue/dry-run/<intent_id>/`
- `POST /api/execution-venue/run-parity/<intent_id>/`
- `GET /api/execution-venue/parity-runs/`
- `GET /api/execution-venue/summary/`

## Venue account mirror module (new)

The backend now includes `apps.venue_account` as a dedicated sandbox external-state layer.

What it does:
- builds canonical snapshot entities:
  - `VenueAccountSnapshot`
  - `VenueBalanceSnapshot`
  - `VenueOrderSnapshot`
  - `VenuePositionSnapshot`
- runs formal parity checks via:
  - `VenueReconciliationRun`
  - `VenueReconciliationIssue`
- exposes REST endpoints under `/api/venue-account/*`.

How it differs from nearby modules:
- `execution_venue` = outgoing payload/response contract and send-parity harness.
- `venue_account` = incoming external-state mirror and account parity diagnostics.
- `broker_bridge` = intent/mapping/validation/dry-run source.

Still out of scope:
- real broker auth/connectivity
- live account sync
- live reconciliation
- real execution/money

## Connector Lab app (new)

`apps.connector_lab` is a technical adapter qualification harness that reuses `execution_venue`, `venue_account`, `go_live_gate`, `certification_board`, and `incident_commander` evidence surfaces while remaining strictly sandbox-only.

Service split:
- `services/cases.py`: explicit qualification catalog.
- `services/fixtures.py`: reusable sandbox fixture profiles.
- `services/qualification.py`: end-to-end suite execution against adapter contract + mirror/reconciliation.
- `services/recommendation.py`: readiness recommendation generation.
- `services/reporting.py`: summary aggregation for dashboards and gate/certification evidence.

Core endpoints:
- `GET /api/connectors/cases/`
- `POST /api/connectors/run-qualification/`
- `GET /api/connectors/runs/`
- `GET /api/connectors/runs/<id>/`
- `GET /api/connectors/current-readiness/`
- `GET /api/connectors/summary/`

Still out of scope:
- real read-only broker connectivity
- real credentials/secrets
- real order routing/execution
- real-money workflows
