# market-trading-bot

Professional initial scaffold for a modular prediction markets intelligence and paper-trading platform. This version is intentionally limited to project structure, local development tooling, a professional frontend shell, and a minimal backend healthcheck.

## Current scope

- **Frontend:** React + Vite + TypeScript application shell with dashboard, navigation, and local backend health visibility.
- **Backend:** Django + Django REST Framework scaffold with `GET /api/health/`.
- **Infrastructure:** Docker Compose services for PostgreSQL and Redis.
- **Architecture:** monorepo organized for future apps, engines, provider adapters, and documentation.

## What this scaffold does not include yet

- Real market provider integrations.
- Authentication or user management.
- Trading or execution logic.
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
- starts the Django dev server and the Vite dev server
- on Windows, opens backend/frontend in separate console windows and leaves the original terminal free
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
python start.py up --no-seed
python start.py up --with-sim-loop
python start.py setup --skip-frontend
python start.py setup --skip-backend
python start.py setup --skip-install
```

### What each command does

- `python start.py` / `python start.py up`: validates prerequisites first, prepares the local environment, starts Postgres + Redis, runs migrations, seeds demo data if needed, and only then launches backend + frontend.
- `python start.py setup`: prepares `.env`, `.venv`, backend/frontend dependencies, Docker services, migrations, and auto-seed logic without starting the dev servers.
- `python start.py status`: prints the current Python interpreter, backend venv python, Node/npm resolution, Docker Compose mode, env/dependency presence, ports, and URLs.
- `python start.py down`: stops launcher-managed backend/frontend processes and runs `docker compose down` (or `docker-compose down`).
- `python start.py seed`: runs `python manage.py seed_markets_demo`.
- `python start.py simulate-tick`: runs one simulation tick with `python manage.py simulate_markets_tick`.
- `python start.py simulate-loop`: runs the existing loop command `python manage.py simulate_markets_loop`.
- `python start.py backend`: prepares and starts only the Django backend.
- `python start.py frontend`: prepares and starts only the Vite frontend.

## Running each part manually

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

Each library currently contains only a README describing its intended future responsibility.

## Documentation

- `apps/frontend/README.md`: frontend setup, routing, healthcheck behavior, and local configuration.
- `docs/architecture/frontend-architecture.md`: frontend layout and routing decisions for this phase.
- `docs/architecture/monorepo-architecture.md`: initial architecture description.
- `docs/prompts-codex/README.md`: guidelines for future Codex-assisted tasks.
- `docs/api/README.md`: placeholder for future API reference material.

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
