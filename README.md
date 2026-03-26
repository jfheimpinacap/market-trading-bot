# market-trading-bot

Professional initial scaffold for a modular prediction markets intelligence and paper-trading platform. This version is intentionally limited to project structure, local development tooling, a professional frontend shell, and a minimal backend healthcheck.

## Current scope

- **Frontend:** React + Vite + TypeScript local-first operator workspace with dashboard, markets, signals, risk, policy approval flow, paper trading, portfolio, post-mortem, automation, semi-auto demo, and system views.
- **Backend:** Django + Django REST Framework modular API with markets demo, signals demo, risk demo, policy engine demo, paper trading, post-mortem, automation, and health endpoints.
- **Position lifecycle:** new `position_manager` layer for open paper holding governance (HOLD/REDUCE/CLOSE/REVIEW_REQUIRED), auditable exit plans, mission-control integration, and operator-queue routing.
- **Research scan:** `research_agent` with RSS + Reddit + optional X/Twitter adapter ingestion, local LLM structured narrative analysis, social normalization, market linking, and mixed-source shortlist generation.
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
- Frontend now also surfaces **paper-tradable vs blocked** status (with backend reason) for real read-only markets in `/markets` and `/markets/:marketId`.
- Real provider data is explorable in `/markets` and `/markets/:marketId` as read-only context.
- Paper trading remains simulated only; no real execution path is enabled from the frontend.

### Semi-autonomous demo mode (current)

The platform now includes a conservative semi-autonomous demo mode:

- evaluate-only proposal classification
- guarded paper-only auto execution for strict AUTO_APPROVE cases
- manual pending approval queue for APPROVAL_REQUIRED outcomes
- explicit hard blocks for policy HARD_BLOCK and safety guardrail failures

Still out of scope: real trading, exchange auth, autonomous schedulers/workers, websockets, and ML/LLM execution.

### Autonomous continuous demo loop (new)

### Evaluation harness (new)

The platform now includes an explicit **benchmark/evaluation harness** for autonomous paper/demo operation:

- objective session/run metrics across proposals, approvals, blocks, executions, reviews, PnL/equity, and safety events
- auditable run records via `EvaluationRun` + `EvaluationMetricSet`
- technical frontend route at `/evaluation` for snapshots, recent run comparisons, and guidance
- strict local-first boundary: no ML, no LLM, no real-money execution

### Experiment runner / strategy profiles (new)

The platform now includes an **experiment runner** for profile-based comparison across replay and live paper evaluation:

- persisted `StrategyProfile` configs (conservative/balanced/aggressive/custom)
- persisted `ExperimentRun` records for replay, live evaluation, and live-vs-replay comparison snapshots
- normalized metrics and `/api/experiments/comparison/` deltas to identify useful/conservative/stable behavior
- frontend route `/experiments` with profile cards, run launcher, run history, and side-by-side comparison table
- strict scope remains paper/demo only: no real money, no real execution, no ML/LLM tuning

### Prediction model governance (new)

Prediction training now includes a formal governance layer for predictor comparison:

- heuristic-vs-heuristic and heuristic-vs-XGBoost comparisons on offline datasets
- scope-aware evaluation (`demo_only`, `real_only`, `mixed`)
- evaluation profiles (`conservative_model_eval`, `balanced_model_eval`, `strict_calibration_eval`)
- auditable recommendation output:
  - `KEEP_HEURISTIC`
  - `KEEP_ACTIVE_MODEL`
  - `ACTIVATE_CANDIDATE`
  - `CAUTION_REVIEW_MANUALLY`
- explicit non-goal: no automatic model switching at runtime


The platform now also includes a controlled **autonomous continuous demo loop** (`/continuous-demo` + `/api/continuous-demo/*`):

- starts, pauses, resumes, and stops continuous background cycles
- supports single manual cycle execution for safe operator testing
- persists session + cycle audit trails
- reuses existing automation and semi-auto services
- remains strictly paper/demo only with explicit kill switch support

Still out of scope: real execution, exchange auth, distributed schedulers, websockets, and LLM agents.

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

### Runtime modes: full vs lite

The launcher now supports two explicit local modes:

- **FULL mode (default):** PostgreSQL + Redis via Docker Compose, Django `config.settings.local`.
- **LITE mode (`--lite`):** SQLite, Docker skipped, Redis optional/disabled, Django `config.settings.lite`.

Examples:

```bash
python start.py --lite
python start.py setup --lite
python start.py up --lite
```

`--lite` can be used from notebooks or machines without Docker. In lite mode the launcher forces `--skip-infra`, runs migrations against SQLite, and keeps the frontend flow unchanged.

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
python start.py up --lite
```

### What each command does

- `python start.py` / `python start.py up`: validates prerequisites first, prepares the local environment, starts Postgres + Redis, runs migrations, seeds demo data if needed, launches backend + frontend in detached mode, waits for both services to respond, opens the browser by default, and then returns control to the same console.
- `python start.py setup`: prepares `.env`, `.venv`, backend/frontend dependencies, infra (or skips infra in lite mode), migrations, and auto-seed logic without starting the dev servers.
- `python start.py status`: prints the current Python interpreter, backend venv python, Node/npm resolution, Docker Compose mode, env/dependency presence, process/runtime readiness, startup mode, and URLs.
- `python start.py down`: stops launcher-managed backend/frontend processes and runs `docker compose down` (or `docker-compose down`).
- `python start.py seed`: runs `python manage.py seed_markets_demo`.
- `python start.py simulate-tick`: runs one simulation tick with `python manage.py simulate_markets_tick`.
- `python start.py simulate-loop`: runs the existing loop command `python manage.py simulate_markets_loop`.
- `python start.py backend`: prepares and starts only the Django backend.
- `python start.py frontend`: prepares and starts only the Vite frontend.

### Lite mode limitations (intentional)

- SQLite is for local portability, not production concurrency.
- Redis is optional/disabled in lite mode; anything requiring external broker behavior should be treated as degraded local-demo behavior.
- Continuous/semi-auto/evaluation flows remain paper/demo oriented and suitable for local iteration, not long-running production sessions.

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


## Safety hardening / guardrails (paper-only)

This repo now includes an explicit **safety guard** layer to harden demo operation before any future autonomy increase:

- exposure caps per market and globally
- auto-trade caps per cycle/session
- drawdown and unrealized-loss thresholds
- cooldown soft-stop and hard-stop transitions
- explicit kill switch policy with manual re-enable
- auditable safety events for warnings/stops/escalations

Still intentionally not implemented: real trading execution, real exchange auth, local LLM, advanced adaptive optimization.

### Learning memory / adaptive heuristics demo (new)

El sistema ahora incluye una capa de **learning memory heurística y auditable** (sin ML/LLM):

- persiste memoria de outcomes recientes desde postmortem/evaluation/safety
- genera ajustes conservadores activos por scope (`global`, `provider`, `source_type`, `signal_type`)
- influye de forma limitada en proposal/risk sin reemplazar policy
- expone `/learning` en frontend y `/api/learning/*` en backend

Sigue fuera de alcance: ML real, entrenamiento automático, LLM local, ejecución real y dinero real.


## Controlled learning loop integration (current)

The platform now closes a controlled learning loop across existing modules:

- automation and continuous demo can trigger a conservative learning-memory rebuild
- every rebuild is persisted as an auditable `LearningRebuildRun`
- rebuilt adjustments continue to influence proposal confidence/quantity and risk caution in later cycles
- defaults remain conservative (manual-first, no per-cycle aggressive rebuild)

Still intentionally out of scope:
- ML training/inference
- local LLM agents
- real money or real execution
- opaque autonomous tuning

### Real-data refresh pipeline hardening (new)

The project now includes a dedicated, auditable read-only sync pipeline for real providers (Kalshi + Polymarket):

- persisted sync run tracking (`ProviderSyncRun`)
- manual sync via API + management command
- provider health signal exposure (`last success`, `last failed`, `consecutive failures`, stale warning)
- strengthened snapshot ingestion path for real read-only markets
- conservative integration hooks for automation and continuous-demo

Still explicitly out of scope:
- real trading execution
- real exchange auth
- websocket/streaming infrastructure
- distributed scheduler/worker orchestration


## Autonomous real-market paper operation scope
- New backend module `real_market_ops` adds conservative autonomous scope for `real_read_only` markets with `paper_demo_only` execution.
- Eligibility centralizes provider health/freshness, paper tradability, open status, pricing sufficiency, and optional liquidity/volume/category constraints.
- API endpoints: `/api/real-ops/evaluate/`, `/api/real-ops/run/`, `/api/real-ops/runs/`, `/api/real-ops/status/`.
- Frontend route `/real-ops` provides controls for evaluation/run, scope summary, provider-sync awareness, and recent run audit table.
- Explicitly out of scope: real exchange auth, real execution adapters, websockets/streaming, and real-money trading.

### Portfolio-aware allocation demo (new)

El sistema ahora incluye una capa explícita de **portfolio-aware capital allocation / execution prioritization** en modo paper/demo:
- ranking heurístico y auditable de propuestas competidoras
- asignación conservadora de cantidad final según cash/exposición/límites
- historial de corridas y decisiones (`AllocationRun`, `AllocationDecision`)
- integración con `semi_auto_demo` y `real_market_ops` antes de autoejecución paper

Se mantiene fuera de alcance: optimización cuantitativa avanzada, Kelly, ML/LLM, y dinero real.

## Operator Queue / Escalation Center (new)

A new centralized operator queue is now available at:
- Backend API: `/api/operator-queue/*`
- Frontend route: `/operator-queue`

What it does:
- unifies approval-required and escalated exceptions in a single inbox
- supports approve/reject/snooze decisions with audit logs
- keeps execution mode strictly paper/demo only

Current source integrations:
- semi-auto pending approvals
- real-ops pending approvals and safety-escalated approvals

Explicitly still out of scope:
- real trading execution
- exchange authentication
- real money
- local LLM
- multi-user approval workflow

### Historical replay / backtest-like simulation demo (new)

The platform now includes a dedicated replay layer (`/replay`, `/api/replay/*`) to run controlled historical simulations using already persisted market snapshots.

Key boundaries:
- uses stored snapshots only (no live streaming dependency during replay)
- reuses proposal/risk/policy/allocation/safety flow where possible
- isolated replay paper account per run to avoid contaminating operational paper account
- audit-friendly persisted artifacts: run-level summary + step-level timeline
- still local-first and paper/demo only (no real money, no real execution)

### Go-live readiness / promotion gates (new)

The platform now includes a dedicated **readiness assessment layer** for formal promotion decisions in paper/demo mode:

- backend app: `apps/readiness_lab`
- API: `/api/readiness/*`
- frontend route: `/readiness`
- persisted `ReadinessProfile` and `ReadinessAssessmentRun`
- explicit gate outcomes (pass/fail/warning), blockers, and recommendations

Important boundary: this does **not** enable real money, real execution, exchange auth, or automatic go-live.

### Runtime promotion controller / operational mode governance (new)

The platform now includes explicit runtime governance for paper/demo autonomy at `/runtime` and `/api/runtime/*`.

Operational modes:
- `OBSERVE_ONLY`
- `PAPER_ASSIST`
- `PAPER_SEMI_AUTO`
- `PAPER_AUTO`

What this adds:
- a persisted runtime mode state (`current_mode`, `status`, `set_by`, rationale, metadata)
- auditable runtime transition logs
- explicit capability matrix per mode
- mode changes constrained by **readiness** + **safety**
- automatic conservative degradation when safety/readiness constraints tighten

Scope remains unchanged:
- paper/demo only
- no real-money execution
- no exchange auth
- no automatic promotion to real trading
- no local LLM integration

## Operator alerts / incident center / digest pipeline (new)

The platform now includes a dedicated **operator alerts layer** for paper/demo operations:

- backend app: `apps/backend/apps/operator_alerts`
- frontend route: `/alerts`
- API base: `/api/alerts/`

What it adds:
- persistent alerts with severity/status/source and dedupe key
- simple aggregation from operator queue, safety, runtime, sync, readiness, and continuous demo modules
- acknowledge/resolve workflow for exception triage
- digest records that summarize recent windows without manually checking multiple screens

What remains intentionally out of scope:
- external notifications (email/SMS/push/chat)
- websockets/realtime infra
- real money / real order execution
- LLM-driven incident narratives

## Notification delivery / escalation routing (new)

Se agregó una capa explícita de **notification delivery / escalation routing** para operadores, manteniendo `operator_alerts` como fuente de verdad del incidente:

- Backend nuevo: `apps.notification_center`
- Entidades: `NotificationChannel`, `NotificationRule`, `NotificationDelivery`
- Canales iniciales: `ui_only` (siempre), `webhook` simple, `email` opcional
- Endpoints:
  - `GET/POST /api/notifications/channels/`
  - `GET/POST /api/notifications/rules/`
  - `GET /api/notifications/deliveries/`
  - `GET /api/notifications/deliveries/<id>/`
  - `POST /api/notifications/send-alert/<alert_id>/`
  - `POST /api/notifications/send-digest/<digest_id>/`
  - `GET /api/notifications/summary/`
- Dedupe/cooldown: ventana por regla + supresión por fingerprint y cooldown por alerta/canal.
- Frontend nuevo: ruta `/notifications` con canales, reglas, historial, resumen y acciones manuales.

Fuera de alcance por diseño: ejecución real, dinero real, LLM local, campañas masivas, orquestación enterprise de mensajería.

### Automatic notification dispatch + digest automation (new)

`notification_center` now supports local-first automation without real-money execution:

- automatic immediate dispatch for relevant/open alerts (rule-driven, dedupe+cooldown preserved)
- automatic digest cycles with conservative cadence (`cycle_window` digests)
- persistence escalation for stale critical/high alerts and repeated warnings
- auditable delivery trace via `NotificationDelivery.trigger_source` (`manual`, `automatic`, `digest_automation`, `escalation`)
- automation state controls via API and `/notifications` UI

Still out of scope: real trading, distributed schedulers, websocket push, and complex multi-tenant notification campaigns.

## Local LLM integration layer (Ollama, new)

The backend now includes a **local-first LLM integration layer** for controlled narrative enrichment (not autonomous decisioning):

- provider: `LLM_PROVIDER=ollama`
- local endpoint: `OLLAMA_BASE_URL=http://localhost:11434`
- configurable chat model: `OLLAMA_CHAT_MODEL`
- configurable embedding model: `OLLAMA_EMBED_MODEL` (default `nomic-embed-text`)
- toggle + timeout: `LLM_ENABLED`, `OLLAMA_TIMEOUT_SECONDS`

Initial use cases:
- proposal thesis enrichment
- post-mortem enriched summary + lessons learned
- learning-note enrichment
- local embeddings endpoint for prototyping

Explicit boundary remains unchanged:
- no real money
- no real execution
- no LLM replacement of risk/policy/safety
- no autonomous LLM trading

## Narrative ingestion + research scan MVP (new)

A first local-first narrative scan/research block is now available:

- Backend app: `apps/backend/apps/research_agent`
- Frontend route: `/research`
- API root: `/api/research/*`

What it does in this phase:
- ingest configurable RSS sources
- deduplicate narrative items
- run structured narrative analysis using local LLM (Ollama) with degraded heuristic fallback
- create heuristic market links against read-only real/demo markets
- generate a persisted shortlist of research candidates with narrative-vs-market relation labels (`alignment` / `divergence` / `uncertainty`)

Out of scope remains unchanged:
- no real-money execution
- no real exchange execution
- no complex X/Twitter/Reddit crawling
- no vector DB/RAG stack
- no LLM authority over risk/policy/safety

## Prediction agent MVP (new)

Se agregó un `prediction_agent` local-first orientado a paper/demo:

- calcula `system_probability`, `market_probability`, `edge`, `confidence` y `rationale`
- persiste `PredictionRun` + `PredictionFeatureSnapshot` + `PredictionScore` para auditoría
- expone API en `/api/prediction/*` y UI en `/prediction`
- integra narrativa (`research_agent`) y ajustes conservadores (`learning_memory`) como señales auxiliares
- alimenta `proposal_engine` como contexto adicional, sin reemplazar risk/policy/safety

Fuera de alcance (intencional en esta fase):
- dinero real / ejecución real
- modelo XGBoost entrenado final
- autoentrenamiento opaco
- reemplazo de guardrails por LLM o por el prediction layer

## Prediction trained-model foundation (new)

The prediction stack now includes an offline training foundation for calibrated tabular models:

- historical dataset build from market snapshots
- initial binary label definition (`future_probability_up_24h`)
- XGBoost training + sigmoid calibration
- model artifact registry + active model switching
- runtime integration with heuristic fallback

Still out of scope: real execution, real money, continuous auto-training loops, AutoML, and replacing risk/policy/safety governance.

## Agent orchestration layer (new)

The platform now includes an explicit **agent orchestration layer** under `/api/agents/*` and frontend `/agents`.

What is included:
- registered agents (scan, research, prediction, risk, postmortem, learning)
- auditable `AgentRun`, `AgentPipelineRun`, and `AgentHandoff` records
- controlled pipelines:
  - `research_to_prediction`
  - `postmortem_to_learning`
  - `real_market_agent_cycle`
- structured handoff payload summaries for traceability

What is intentionally not included yet:
- real-money trading
- real execution routing
- opaque autonomous multi-agent planners
- black-box LLM authority over system decisions

This layer reuses existing modules (research/prediction/risk/postmortem/learning) and does not replace their internal domain logic.


## Risk agent refinement (paper/demo only)
- New `apps/backend/apps/risk_agent/` module introduces structured `RiskAssessment`, `RiskSizingDecision`, `PositionWatchRun`, and `PositionWatchEvent`.
- Separation of concerns is explicit: prediction estimates; risk evaluates/sizes; policy authorizes; safety limits; runtime governs mode.
- API endpoints: `POST /api/risk-agent/assess/`, `POST /api/risk-agent/size/`, `POST /api/risk-agent/run-watch/`, `GET /api/risk-agent/assessments/`, `GET /api/risk-agent/watch-events/`, `GET /api/risk-agent/summary/`.
- Frontend route `/risk-agent` provides assessment, sizing, watch loop, and audit history panels.
- Out of scope remains unchanged: no real money, no real execution, no production-grade Kelly optimizer, no exchange stop-loss automation.

## Postmortem multi-agent board (new)

The platform now includes a local-first **postmortem board / loss review committee**:

- runs explicit perspective reviewers (narrative, prediction, risk, runtime, learning)
- stores auditable per-perspective records and a final structured conclusion
- integrates into learning memory with conservative handoff
- adds an explicit agent pipeline: `postmortem_board_cycle`
- remains strictly paper/demo only with no real-money or real-execution path

## Research universe scanner / triage board (new)

`research_agent` now includes a formal **universe scanner + market triage board** layer:

- explicit `MarketUniverseScanRun` runs with auditable counters (considered, filtered, shortlisted, watchlist)
- transparent `MarketTriageDecision` records with score, status, reasons, and flags
- explicit `PursuitCandidate` outputs for markets worth pursuing (`shortlisted` / `watch`)
- profile-based thresholds (`conservative_scan`, `balanced_scan`, `broad_scan`)
- narrative remains a contextual boost/caution signal (not a mandatory gate)
- handoff path from triage board to prediction pipeline (`run-triage-to-prediction`)

Scope remains local-first and **paper/demo only**: no real money, no real execution, no opaque optimizer/planner.


### Signal fusion agent / opportunity board (new)

A formal signal fusion layer now exists inside `apps.signals` to consolidate:
- research triage/pursuit output
- prediction scores (system probability, edge, confidence)
- risk assessment/sizing
- runtime + safety constraints

This layer produces ranked `OpportunitySignal` records and explicit `ProposalGateDecision` outputs before proposal generation.

Still out of scope:
- real-money trading
- real execution
- opaque planners/optimizers
- LLM final authority

## Opportunity supervisor cycle (new)

A new backend+frontend layer now provides an auditable **end-to-end autonomous opportunity cycle** in **paper/demo mode only**.

- Backend module: `apps/backend/apps/opportunity_supervisor/`
- API base: `/api/opportunities/*`
- Frontend route: `/opportunities`

Cycle flow:
1. signal-fusion run (research + prediction + risk context)
2. proposal generation for proposal-ready opportunities
3. allocation pre-check per generated proposal
4. governance path resolution using runtime + policy + safety
5. final path persistence (`WATCH`, `PROPOSAL_ONLY`, `QUEUE`, `AUTO_EXECUTE_PAPER`, `BLOCKED`)

Explicitly still out of scope:
- real-money execution
- exchange auth/order routing
- opaque free-form planner

### Mission control loop (new)

The platform now includes a formal **mission control** layer (`/mission-control`, `/api/mission-control/*`) to run periodic autonomous paper/demo operations with explicit loop governance:

- persistent mission sessions, cycles, and step-level traces
- explicit start/pause/resume/stop/run-cycle controls
- cadence-based optional steps (research/universe scan, risk watch, digest, postmortem refresh, learning rebuild)
- `opportunity_supervisor` remains the central execution-path engine inside each cycle
- runtime governor + safety guard remain authoritative (mission control degrades/skips when blocked)
- no real-money execution and no real trading path

Out of scope remains unchanged: distributed schedulers, cluster orchestration, and real execution.
