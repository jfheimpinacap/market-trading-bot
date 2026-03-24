# market-trading-bot

Professional initial scaffold for a modular prediction markets intelligence and paper-trading platform. This version is intentionally limited to project structure, local development tooling, a professional frontend shell, and a minimal backend healthcheck.

## Current scope

- **Frontend:** React + Vite + TypeScript local-first operator workspace with dashboard, markets, signals, risk, policy approval flow, paper trading, portfolio, post-mortem, automation, and system views.
- **Backend:** Django + Django REST Framework modular API with markets demo, signals demo, risk demo, policy engine demo, paper trading, post-mortem, automation, and health endpoints.
- **Infrastructure:** Docker Compose services for PostgreSQL and Redis.
- **Architecture:** monorepo organized for future apps, engines, provider adapters, and documentation.

### Real data UX boundary (current)


### Paper trading on real-market data (current)

The backend now supports **paper trading using real read-only market data**:

- real market data can be ingested and used as paper pricing reference
- execution still stays `paper_demo_only` with fictional cash/positions/trades
- risk/policy/proposal flows can evaluate trades on real read-only markets
- serializers expose explicit source/execution context for frontend clarity

Still not implemented: real auth, real order placement, real portfolio sync, or real execution paths.


- Frontend markets views now distinguish **demo/local** markets from **real/read-only** markets with explicit source badges and filters.
- Real provider data is explorable in `/markets` and `/markets/:marketId` as read-only context.
- Paper trading remains simulated only; no real execution path is enabled from the frontend.

## What this scaffold does not include yet

- Real trading provider integrations (execution/auth).
- Note: real **read-only** market-data ingestion is now available for Kalshi and Polymarket.
- Authentication or user management.
- Real trading or provider execution logic.
- ML, forecasting models, or agent orchestration.
- Production deployment configuration.

## Technology stack

- **Frontend:** React, Vite, TypeScript
- **Backend:** Django, Django REST Framework, Celery
- **Data & messaging:** PostgreSQL, Redis
- **Developer tooling:** Docker Compose, Makefile, shell scripts

## Repository structure

```text
market-trading-bot/
├── apps/
│   ├── backend/
│   └── frontend/
├── docs/
│   ├── api/
│   ├── architecture/
│   └── prompts-codex/
├── infra/
│   ├── docker/
│   └── scripts/
├── libs/
│   ├── common-utils/
│   ├── feature-store/
│   ├── provider-core/
│   ├── provider-kalshi/
│   └── provider-polymarket/
├── services/
│   ├── execution-engine/
│   ├── market-discovery/
│   ├── postmortem-engine/
│   ├── probability-engine/
│   ├── risk-engine/
│   └── source-intelligence/
├── .env.example
├── .editorconfig
├── .gitignore
├── docker-compose.yml
└── Makefile
```

## Local setup

### Recommended flow: `start.py`

The repository now includes a project-specific launcher at the repo root:

```bash
python start.py
```

That default command is equivalent to:

```bash
python start.py up
```

What the launcher does for this monorepo:

- validates the expected repo structure (`apps/backend`, `apps/frontend`, `docker-compose.yml`)
- checks local prerequisites such as Python, Node.js, npm, and Docker Compose
- resolves `node`/`node.exe` and `npm`/`npm.cmd` explicitly on Windows so PowerShell and VS Code terminals behave correctly
- creates `.env` files from `.env.example` when they are missing
- creates `apps/backend/.venv` when needed
- installs backend requirements only when `requirements.txt` changes
- installs frontend dependencies only when `package.json` or `package-lock.json` changes
- starts PostgreSQL and Redis with Docker Compose
- runs Django migrations
- auto-seeds demo markets only when the database has no `Market` rows yet
- validates backend and frontend preparation before launching long-lived dev processes so the system is not left half-started
- starts the Django dev server and the Vite dev server in detached background mode by default
- waits for `http://localhost:8000/api/health/` and `http://localhost:5173/` to respond before declaring success
- opens the browser automatically to `http://localhost:5173/system` unless you disable it
- keeps a launcher state file in `.tmp/start-state.json` so `python start.py down` can stop launcher-managed processes later
- keeps the default workflow in a single console on Windows instead of opening two extra terminal windows
- optionally starts the local simulation loop

### Main launcher commands

```bash
python start.py
python start.py up
python start.py setup
python start.py status
python start.py down
python start.py seed
python start.py simulate-tick
python start.py simulate-loop
python start.py backend
python start.py frontend
```

Useful optional flags:

```bash
python start.py --no-browser
python start.py --separate-windows
python start.py up --no-seed
python start.py up --skip-seed
python start.py up --skip-infra
python start.py up --with-sim-loop
python start.py setup --skip-frontend
python start.py setup --skip-backend
python start.py setup --skip-install
```

### What each command does

- `python start.py` / `python start.py up`: validates prerequisites first, prepares the local environment, starts Postgres + Redis, runs migrations, seeds demo data if needed, launches backend + frontend in detached mode, waits for both services to respond, opens the browser by default, and then returns control to the same console.
- `python start.py setup`: prepares `.env`, `.venv`, backend/frontend dependencies, Docker services, migrations, and auto-seed logic without starting the dev servers.
- `python start.py status`: prints the current Python interpreter, backend venv python, Node/npm resolution, Docker Compose mode, env/dependency presence, process/runtime readiness, startup mode, and URLs.
- `python start.py down`: stops launcher-managed backend/frontend processes and runs `docker compose down` (or `docker-compose down`).
- `python start.py seed`: runs `python manage.py seed_markets_demo`.
- `python start.py simulate-tick`: runs one simulation tick with `python manage.py simulate_markets_tick`.
- `python start.py simulate-loop`: runs the existing loop command `python manage.py simulate_markets_loop`.
- `python start.py backend`: prepares and starts only the Django backend.
- `python start.py frontend`: prepares and starts only the Vite frontend.

## Running each part manually

## Recommended launcher UX

The daily local-first workflow is now:

```bash
python start.py
```

That single command now:

1. validates prerequisites
2. prepares `.env`, backend, frontend, and local infra
3. runs migrations
4. auto-seeds demo data when needed
5. starts backend and frontend in background/detached mode
6. waits until backend and frontend really answer HTTP requests
7. opens `http://localhost:5173/system` automatically
8. prints a final “system ready” summary in the original console

If you want the older debug-style behavior with separate Windows terminals:

```bash
python start.py --separate-windows
python start.py up --separate-windows
```

If you do not want the browser to open automatically:

```bash
python start.py --no-browser
python start.py up --no-browser
```

To stop everything that the launcher started:

```bash
python start.py down
```

You can still use the existing manual commands if you want finer control.

### PostgreSQL and Redis

```bash
docker compose up -d postgres redis
docker compose down
```

### Backend

```bash
cd apps/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Healthcheck endpoint:

```text
GET http://localhost:8000/api/health/
```

### Frontend

```bash
cd apps/frontend
cp .env.example .env
npm install
npm run dev
npm run build
```

Important frontend environment variable:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Current modules

### Apps
- `apps/frontend`: local-first dashboard shell with multi-page navigation and backend health visibility.
- `apps/backend`: API scaffold and project configuration.

### Services
- `source-intelligence`
- `market-discovery`
- `probability-engine`
- `risk-engine`
- `execution-engine`
- `postmortem-engine`

Each service currently contains only a README describing its intended future responsibility.

### Libraries
- `provider-core`
- `provider-kalshi`
- `provider-polymarket`
- `feature-store`
- `common-utils`

Provider libraries now include a first read-only implementation for market-data ingestion (Kalshi + Polymarket) plus shared provider-core abstractions.

## Documentation

- `apps/frontend/README.md`: frontend setup, routing, healthcheck behavior, and local configuration.
- `docs/architecture/frontend-architecture.md`: frontend layout and routing decisions for this phase.
- `docs/architecture/monorepo-architecture.md`: initial architecture description.
- `docs/prompts-codex/README.md`: guidelines for future Codex-assisted tasks.
- `docs/api/README.md`: placeholder for future API reference material.

## Demo flow guide

The current local demo is intended to be exercised in this order:

1. open `/` to verify environment health and cross-module indicators
2. review `/signals` or `/markets` to find a market worth inspecting
3. open `/markets/:marketId` to review the market, run the demo risk check, and execute a paper trade
4. open `/portfolio` to inspect the new position, trade history, equity impact, and snapshot changes
5. open `/postmortem` to review the trade outcome and jump back to the related market or portfolio context

If the local environment is empty, you may still need to run some backend demo commands first:

```bash
cd apps/backend && python manage.py seed_paper_account
cd apps/backend && python manage.py generate_demo_signals
cd apps/backend && python manage.py generate_trade_reviews
```

## Helpful commands

```bash
python start.py
python start.py status
python start.py down
python start.py backend
python start.py frontend
make install-frontend
make install-backend
make frontend-dev
make frontend-build
make backend-dev
make backend-migrate
make backend-check
make infra-up
make infra-down
```

## Pending work

- Add domain data and APIs beyond the health monitoring scaffold.
- Upgrade placeholder pages into feature modules progressively.
- Introduce shared contracts for future provider adapters.
- Add containerization for the frontend and backend apps.
- Expand architecture decisions, contribution guidance, and test coverage.

## Summary

This repository is now ready to serve as the base for staged implementation. The current version is a clean, local-first scaffold designed to grow without introducing premature business logic.

## Guided demo automation

The repo now includes a guided demo automation layer that sits on top of the existing local workflow. It exposes explicit backend actions and a frontend `/automation` control center so an operator can move the demo forward without running every step from the terminal.

Included actions:

- simulation tick
- demo signal generation
- paper portfolio revalue
- trade review generation
- lightweight demo state sync
- full demo cycle orchestration

Out of scope by design:

- auto-trading
- periodic scheduling
- real background workers
- websockets
- autonomous agents
- real provider integrations

## Current end-to-end demo flow

The monorepo now supports a local-first demo workflow that looks like this:

`market -> signal -> risk -> policy -> trade -> portfolio -> review -> automation`

A new policy engine / approval rules layer now governs proposed demo trades before execution. It returns one of three explicit outcomes:

- `AUTO_APPROVE`
- `APPROVAL_REQUIRED`
- `HARD_BLOCK`

This layer is intentionally deterministic and auditable. It does **not** use ML, real providers, autonomous agents, or live auto-trading.


## Real data ingestion (read-only)

From `apps/backend` run:

```bash
python manage.py ingest_kalshi_markets --limit 50 --active-only
python manage.py ingest_polymarket_markets --limit 50 --active-only
```

These commands only ingest public market data. They do **not** place orders and do **not** require trading authentication.
