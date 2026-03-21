# market-trading-bot

Professional initial scaffold for a modular prediction markets intelligence and paper-trading platform. This version is intentionally limited to project structure, local development tooling, a placeholder frontend, and a minimal backend healthcheck.

## Current scope

- **Frontend:** React + Vite + TypeScript placeholder dashboard.
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

1. Copy the environment template.
   ```bash
   cp .env.example .env
   ```
2. Start PostgreSQL and Redis.
   ```bash
   docker compose up -d postgres redis
   ```
3. Install backend dependencies.
   ```bash
   cd apps/backend
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```
4. Install frontend dependencies.
   ```bash
   cd apps/frontend
   npm install
   npm run dev
   ```

## Running each part

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
npm install
npm run dev
npm run build
```

## Current modules

### Apps
- `apps/frontend`: user-facing web UI scaffold.
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

- `docs/architecture/monorepo-architecture.md`: initial architecture description.
- `docs/prompts-codex/README.md`: guidelines for future Codex-assisted tasks.
- `docs/api/README.md`: placeholder for future API reference material.

## Helpful commands

```bash
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

- Add frontend routing and domain feature slices.
- Define backend domain APIs beyond health monitoring.
- Introduce shared types/contracts for provider adapters.
- Add containerization for the frontend and backend apps.
- Expand architecture decisions, contribution guidance, and test coverage.

## Summary

This repository is now ready to serve as the base for staged implementation. The current version is a clean scaffold only, designed to grow without introducing premature business logic.
