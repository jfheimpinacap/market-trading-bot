# market-trading-bot

Professional initial scaffold for a modular prediction markets intelligence and paper-trading platform. This version is intentionally limited to project structure, local development tooling, a professional frontend shell, and a minimal backend healthcheck.

## Current scope

- **Frontend:** React + Vite + TypeScript local-first operator workspace with dashboard, markets, signals, risk, policy approval flow, paper trading, portfolio, post-mortem, automation, semi-auto demo, and system views.
- **Backend:** Django + Django REST Framework modular API with markets demo, signals demo, risk demo, policy engine demo, paper trading, post-mortem, automation, and health endpoints.
- **Position lifecycle:** new `position_manager` layer for open paper holding governance (HOLD/REDUCE/CLOSE/REVIEW_REQUIRED), auditable exit plans, mission-control integration, and operator-queue routing.
- **Research scan:** `research_agent` with RSS + Reddit + optional X/Twitter adapter ingestion, local LLM structured narrative analysis, social normalization, market linking, and mixed-source shortlist generation.
- **Infrastructure:** Docker Compose services for PostgreSQL and Redis.
- **Architecture:** monorepo organized for future apps, engines, provider adapters, and documentation.
- **Precedent-aware decision support (new):** research, prediction, risk, signal-fusion, and postmortem now consume semantic precedents automatically in internal flows with conservative influence and explicit audit trails (`AgentPrecedentUse`).

### Precedent-aware agents (new)

- Memory is now used as **decision support**, not as an opaque planner.
- Core sequence:
  1) retrieval (`MemoryRetrievalRun` + `RetrievedPrecedent`)
  2) precedent summary (`top similar cases`, `failure modes`, `lessons`)
  3) conservative influence suggestion (`context_only`, `caution_boost`, `confidence_adjust`, `rationale_only`)
  4) auditable use record (`AgentPrecedentUse`)
- Influence is bounded: it can add caution/reduce confidence/rationale, but it does **not** replace core numeric policy/risk/safety gates.
- Still local-first, single-user, and paper/demo only.

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

### Execution-aware replay / evaluation realism / readiness impact (new)

The platform now supports a practical execution realism bridge across replay, evaluation, experiments, and readiness:

- replay runs accept `execution_mode=naive|execution_aware` and `execution_profile=optimistic_paper|balanced_paper|conservative_paper`
- execution-aware replay routes orders through `execution_simulator` (paper orders, attempts, fills, partial/no-fill, slippage, cancel/expire)
- replay stores `execution_impact_summary` for auditable metrics:
  - `fill_rate`, `partial_fill_rate`, `no_fill_rate`
  - `avg_slippage_bps`, `execution_adjusted_pnl`, `execution_drag`
  - `execution_realism_score`, `execution_quality_bucket`
- evaluation snapshots include execution-adjusted metadata so historical snapshots are less optimistic than perfect-fill assumptions
- experiments can compare naive vs execution-aware metrics and expose execution drag deltas
- readiness now applies an explicit execution-realism penalty when evidence is weak or fill realism is poor

Still out of scope: real money, real routing, institutional microstructure modeling, complex hedging, and opaque planner authority.

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


### Incident commander / degraded mode orchestration (new)

A formal `incident_commander` backend layer now coordinates conservative failure handling across runtime, mission control, rollout, alerts/notifications, and operator queue:

- formal incident entities (`IncidentRecord`, `IncidentAction`, `IncidentRecoveryRun`)
- explicit degraded mode state (`DegradedModeState`)
- conservative mitigation policies (pause/degrade/rollback/disable auto-exec/manual review)
- bounded self-healing retries with full audit trail
- dedicated operator route `/incidents` for current degraded state + incident history

Still out of scope: real-money execution, real execution routing, opaque black-box remediation, and distributed orchestration.


### Operator cockpit / command center (new)

A new desktop-first `/cockpit` route now provides a **single-pane operational control** for manual-first supervision:

- central posture: runtime status, degraded mode, certification, and profile regime
- mission operations panel with cycle context and incident impact
- risk/exposure panel with portfolio throttle + `REVIEW_REQUIRED` position pressure
- execution/venue panel with broker-bridge validation, parity gaps, and reconciliation mismatches
- change-governance panel with promotion, rollout, and champion/challenger status
- severity-based attention queue (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with trace drill-down buttons
- quick actions that trigger existing controls (mission control, incident detection, certification, governance, rollout pause/rollback)

Scope remains unchanged: local-first, single-user, paper/sandbox only, and no real-money execution.

### Autonomy advisory board / insight action emitter (new)

The platform now includes a formal `autonomy_advisory` layer (`/api/autonomy-advisory/*` + `/autonomy-advisory`) to convert reviewed `autonomy_insights` outputs into auditable manual-first artifacts:

- consumes `CampaignInsight` and recommendation targets from `autonomy_insights`
- emits formal artifacts (`MEMORY_PRECEDENT_NOTE`, `ROADMAP_GOVERNANCE_NOTE`, `SCENARIO_CAUTION_NOTE`, `PROGRAM_POLICY_NOTE`, `MANAGER_REVIEW_NOTE`)
- tracks advisory runs, recommendation queue, blocked/manual-review states, and duplicate-skip outcomes
- keeps explicit links/stubs toward memory/feedback/program contexts without auto-applying changes

Out of scope remains explicit: no real-money trading, no real broker/exchange execution, no opaque auto-apply, and no black-box planner.

### Policy rollout guard / post-change baselining loop (new)

The stack now includes a dedicated `policy_rollout` layer (`/api/policy-rollout/*` + `/policy-rollout`) that closes the post-change governance loop after `policy_tuning` apply:

- starts a formal observation run from an **already applied** policy tuning candidate
- captures explicit **baseline snapshot** and **post-change snapshot**
- compares before/after deltas for approvals, friction, auto-success, incidents, and manual intervention
- emits recommendation-first outcomes:
  - `KEEP_CHANGE`
  - `REQUIRE_MORE_DATA`
  - `ROLLBACK_CHANGE`
  - `REVIEW_MANUALLY`
  - `STABILIZE_AND_MONITOR`
- supports **manual rollback only** (no silent auto-rollback), with audit metadata and optional approval-center gate

Deliberate non-goals remain unchanged: no real money, no real execution, no opaque auto-apply/auto-rollback planner, single-user local-first scope.

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

## Portfolio governor / exposure manager (new)

Se añadió una capa formal de gobernanza de cartera (`apps/backend/apps/portfolio_governor`) para paper/demo only:

- snapshot agregado de exposición (equity, cash, exposure total, concentración por market/provider/category, drawdown proxy)
- señales de régimen auditables (`normal`, `concentrated`, `drawdown_caution`, `capital_tight`, etc.)
- decisión de throttling global (`NORMAL`, `CAUTION`, `THROTTLED`, `BLOCK_NEW_ENTRIES`)
- integración con `opportunity_supervisor`, `mission_control`, `runtime_governor` y `safety_guard`

Scope explícito:
- sí: throttling transparente por reglas
- no: dinero real, ejecución real, hedging complejo, optimizador institucional, planner opaco

## Adaptive profile manager / meta-governance (new)

A formal paper/demo-only `profile_manager` layer now coordinates adaptive operating profiles across research, signals, opportunity supervisor, mission control, and portfolio governor.

- classifies regime (`NORMAL`, `CAUTION`, `STRESSED`, `CONCENTRATED`, `DRAWDOWN_MODE`, `DEFENSIVE`, `BLOCKED`)
- emits auditable `ProfileDecision` records with reason codes and constraints
- separates recommendation vs application (`RECOMMEND_ONLY`, `APPLY_SAFE`, `APPLY_FORCED`)
- treats runtime/safety/readiness as higher authority and never bypasses them
- exposes `/profile-manager` UI + `/api/profile-manager/*` endpoints

Still out of scope: real-money execution, opaque planner behavior, RL/ML meta-controller, and LLM final authority.


## Paper execution realism layer
- Added `execution_simulator` to model paper order lifecycle (`PaperOrder`, `PaperExecutionAttempt`, `PaperFill`) with partial/no-fill, slippage, cancel/expire handling.
- This layer is **paper/demo only** and intentionally excludes real routing/exchange execution.

## Champion-Challenger shadow benchmark supervisor (new)

The platform now includes a dedicated **champion-challenger shadow mode** (`/champion-challenger` + `/api/champion-challenger/*`) for continuous live-paper benchmarking:

- explicit `StackProfileBinding` for champion and challenger stacks
- shadow-only benchmark runs (`ChampionChallengerRun`) with no real-money and no real execution
- execution-aware comparison metrics (fill rate, partial/no-fill, execution-adjusted pnl, execution drag)
- decision-divergence and risk/review pressure deltas
- recommendation output for governance follow-up:
  - `KEEP_CHAMPION`
  - `CHALLENGER_PROMISING`
  - `CHALLENGER_UNDERPERFORMS`
  - `REVIEW_MANUALLY`

Design boundaries:
- no automatic champion switching
- no hidden planner authority
- no RL auto-optimization
- no real-money execution

This complements prediction model governance and profile manager evidence without duplicating them.

## Semantic memory / precedent retrieval layer (new)

A local-first semantic memory layer is now available at `apps/backend/apps/memory_retrieval` with frontend visibility in `/memory`.

What it adds:
- formal memory entities: `MemoryDocument`, `MemoryRetrievalRun`, `RetrievedPrecedent`
- local embedding generation via existing `llm_local` embeddings (Ollama-compatible)
- simple in-process cosine retrieval (no external vector DB required)
- auditable run/result traceability for precedent retrieval
- case-based summary for caution signals, failure modes, and lessons learned

Primary API endpoints:
- `POST /api/memory/index/`
- `POST /api/memory/retrieve/`
- `GET /api/memory/documents/`
- `GET /api/memory/retrieval-runs/`
- `GET /api/memory/retrieval-runs/<id>/`
- `GET /api/memory/summary/`

Integrated assist endpoints:
- `POST /api/research/precedent-assist/`
- `POST /api/prediction/precedent-assist/`
- `POST /api/risk-agent/precedent-assist/`
- `POST /api/postmortem-board/precedent-compare/`

Out of scope remains unchanged: real money, real execution, heavy enterprise RAG stack, opaque planners.

### Stack promotion committee / controlled evolution pipeline (new)

A formal `promotion_committee` layer now provides conservative and auditable stack-change governance in paper/demo mode:

- consolidates evidence from champion-challenger, readiness, execution-aware deltas, profile governance, portfolio governor context, model governance, and precedent warnings
- emits clear recommendation codes:
  - `KEEP_CURRENT_CHAMPION`
  - `PROMOTE_CHALLENGER`
  - `EXTEND_SHADOW_TEST`
  - `REVERT_TO_CONSERVATIVE_STACK`
  - `MANUAL_REVIEW_REQUIRED`
- distinguishes recommendation-only vs explicit manual apply
- stores review runs + decision logs for traceability
- exposes `/promotion` UI route and `/api/promotion/*` API endpoints

Still out of scope:
- real money
- real execution
- opaque auto-promotion or auto-switching
- RL/auto-optimization


### Stack rollout manager / canary promotion / rollback guardrails (new)

A new `rollout_manager` layer now operationalizes promotion recommendations with explicit gradual rollout in paper/demo mode:

- explicit rollout plans (`SHADOW_ONLY`, `CANARY`, `STAGED`) with deterministic canary percentage routing
- persisted rollout runs with routed/champion/challenger/canary counters
- explicit guardrail events and rollout decisions (`CONTINUE_ROLLOUT`, `PAUSE_ROLLOUT`, `ROLLBACK_NOW`, `COMPLETE_PROMOTION`, `EXTEND_CANARY`)
- explicit rollback action back to champion-only routing with auditable reason
- integration touchpoints with mission control and opportunity supervisor

Boundary remains strict:
- no real-money execution
- no real order routing
- no opaque full auto-switching

### Chaos lab / fault injection / resilience benchmark (new)

The platform now includes a formal `chaos_lab` layer to actively validate resilience in paper/demo mode:

- controlled and reversible fault injection scenarios (`/api/chaos/experiments/`, `/api/chaos/run/`)
- auditable run traces (`ChaosRun`, `ChaosObservation`)
- resilience benchmark snapshots (`ResilienceBenchmark`) with detection/mitigation/recovery metrics and a simple transparent score
- explicit integration with `incident_commander`, `mission_control`, `rollout_manager`, alerts, notifications, and operator queue

Scope boundaries remain unchanged: no real money, no real execution, no distributed chaos orchestration.


### Operational certification board / paper go-live gate (new)

The platform now includes a formal `certification_board` layer for **paper-only** operational certification.

What it adds:
- consolidated evidence snapshot across readiness, chaos/resilience, incidents, champion/challenger, promotion, rollout, runtime/safety, profile and portfolio governance, and execution-aware evaluation
- explicit certification levels and recommendation codes
- auditable operating envelope output (autonomy limits, entry/sizing caps, profile constraints)
- manual-first run/apply workflow with clear logs

What it explicitly does not add:
- real money
- real order execution
- automatic opaque go-live
- auto-promotion to real capital


### Broker bridge sandbox / dry-run routing readiness layer (new)

A new `broker_bridge` layer now prepares the platform for eventual real execution **without crossing into real trading**:

- maps internal sources (currently paper orders and explicit manual payloads) into `BrokerOrderIntent`
- validates intents against certification envelope, runtime, safety, degraded mode, and open critical incidents
- records a `BrokerDryRun` simulated broker response (`accepted`, `rejected`, `hold`, `needs_manual_review`)
- creates operator queue review context when blocked/manual review is required
- exposes `/api/broker-bridge/*` endpoints and frontend route `/broker-bridge`

Boundary remains strict:
- no real broker credentials
- no real order routing
- no real money or account reconciliation

### Go-live rehearsal gate + capital firewall (new)

The platform now includes a formal `go_live_gate` layer to rehearse final pre-live workflows while still blocking live execution by default:

- persisted pre-live checklist runs
- manual approval requests
- final rehearsal run on broker-like intents (dry-run only)
- explicit capital firewall rules that keep live transition disabled
- API endpoints at `/api/go-live/*` and frontend route `/go-live`

This is a preparation layer only. Still out of scope: live credentials, live broker routing, real money, and real order submission.

## Execution venue abstraction (new)

A new backend/frontend layer now formalizes the final **execution venue contract** without enabling any real routing:

- Backend app: `apps/backend/apps/execution_venue`
- Frontend route: `/execution-venue`
- API base: `/api/execution-venue/*`

What it adds:
- canonical external order payload model (`VenueOrderPayload`)
- normalized venue response model (`VenueOrderResponse`)
- capability contract (`VenueCapabilityProfile`) with `live_supported=false`
- parity harness (`VenueParityRun`) to compare broker bridge dry-run, simulator context, and sandbox adapter behavior
- default `NullSandboxVenueAdapter` that never submits real orders

Still explicitly out of scope:
- broker credentials
- real broker/exchange connectivity
- live order placement
- real-money execution or reconciliation

## Venue account mirror / reconciliation sandbox (new)

A new `venue_account` layer completes the **incoming external bridge** in sandbox mode:

- canonical external-style snapshots for account, balances, orders, and positions
- mirror-building from existing `execution_venue` payload/response artifacts plus `execution_simulator`/`paper_trading` state
- formal reconciliation runs (`PARITY_OK` / `PARITY_GAP`) and explicit issue types (missing order mappings, fill drift, status mismatch, balance drift, stale snapshot)
- frontend route `/venue-account` for operational parity visibility

Boundary remains strict:
- sandbox-only (`SANDBOX_ONLY`)
- no broker credentials
- no real account connections
- no real order placement or real-money execution

## Connector Lab: venue connector certification suite (new)

A new sandbox-only **connector_lab** boundary is now available to certify future venue adapters before any read-only/live integration.

- Backend API under `/api/connectors/*` runs formal qualification suites for capabilities, payload mapping, response normalization, account mirror, and reconciliation.
- Readiness outputs include recommendation codes such as `SANDBOX_CERTIFIED`, `READ_ONLY_PREPARED`, `INCOMPLETE_MAPPING`, `RECONCILIATION_GAPS`, and `NOT_READY`.
- Frontend route `/connectors` provides qualification controls, readiness card, case results table, and recent runs.
- This does **not** add real broker connectivity, credentials, live routing, real orders, or real money.

## Unified trace explorer / decision provenance (new)

The platform now includes a dedicated local-first provenance layer for end-to-end auditing without rewriting existing modules:

- Backend app: `apps/backend/apps/trace_explorer`
- API base: `/api/trace/*`
- Frontend route: `/trace`

What it adds:
- trace roots (`market`, `opportunity`, `proposal`, `paper_order`, `venue_order_snapshot`, `incident`, `mission_cycle`)
- trace nodes and causal edges across research → prediction → risk → signals → proposal → allocation → execution → venue → incidents
- unified inclusion of agent orchestrator runs/handoffs and memory precedent use
- compact provenance snapshot for operator/debug/audit workflows
- auditable query history (`TraceQueryRun`)

Still out of scope:
- real money
- live broker execution
- distributed enterprise graph infrastructure
- opaque planner authority
- multi-user enterprise tenancy


## Runbook engine / operator playbooks

The platform now includes a manual-first **runbook engine** for guided remediation workflows.

- Backend module: `apps/backend/apps/runbook_engine/`
- API surface: `/api/runbooks/*`
- Frontend route: `/runbooks`

This layer orchestrates and records operator workflows for incidents, degraded mode, rollout/certification/venue parity issues, queue pressure, and related operational states. It reuses existing module actions (mission control, incidents, rollout, certification, venue reconciliation, trace) and does **not** introduce real money, live execution, or opaque automation.

### Trust-tiered automation policy matrix (new)

The stack now includes a formal **automation policy matrix / supervised runbook autopilot** layer:

- explicit automation profiles (`conservative_manual_first`, `balanced_assist`, `supervised_autopilot`)
- explicit trust tiers (`MANUAL_ONLY`, `APPROVAL_REQUIRED`, `SAFE_AUTOMATION`, `AUTO_BLOCKED`)
- auditable decisions for every evaluated action
- explicit action logs for every auto-execution attempt
- effective tier downgrade by runtime/safety/certification/degraded posture
- hard block for live-execution domains

New operator route: `/automation-policy`.

Scope remains unchanged: local-first, single-user, and paper/sandbox only.

### Supervised runbook autopilot (new)

A new **supervised runbook autopilot / approval-aware closed-loop remediation executor** now extends `runbook_engine` without replacing manual workflows:

- per-step policy resolution through `automation_policy` trust tiers
- safe actions can auto-execute step-by-step
- orchestration pauses for `APPROVAL_REQUIRED` or `MANUAL_ONLY`
- orchestration blocks on guardrail/policy `BLOCKED`
- explicit approval checkpoints, resume, and step retry with audit trails
- cockpit now surfaces paused/blocked autopilot pressure

Strict boundaries remain unchanged:
- local-first
- single-user
- paper/sandbox only
- no real money
- no real execution
- no black-box autonomous remediation

### Approval center / unified decision gates (new)

A new manual-first `/approvals` control plane now centralizes human decisions that were previously scattered across modules.

- Backend app: `apps/backend/apps/approval_center`
- Central entities: `ApprovalRequest`, `ApprovalDecision`
- Sources integrated now: runbook checkpoints, go-live approval requests, and `operator_queue` items marked `approval_required`
- Explicit actions: approve / reject / expire / escalate
- Every decision is auditable and links back to source context + trace roots
- Approving go-live requests in this phase **does not enable live trading** (still rehearsal + paper/sandbox only)

Out of scope remains unchanged: no real money, no real execution, no opaque black-box automation, no enterprise multi-user approval chains.


### Trust calibration governance loop (new)

A dedicated `trust_calibration` layer now closes the human-feedback loop between `approval_center` and `automation_policy` with explicit, auditable analytics.

- consolidates approval outcomes, automation decisions/action logs, and incident aftermath into feedback snapshots
- computes explicit friction/success/reversal metrics by action domain
- emits conservative recommendation-only trust-tier suggestions (`PROMOTE_TO_SAFE_AUTOMATION`, `KEEP_APPROVAL_REQUIRED`, `DOWNGRADE_TO_MANUAL_ONLY`, `BLOCK_AUTOMATION_FOR_ACTION`, `REQUIRE_MORE_DATA`, `REVIEW_RULE_CONDITIONS`)
- adds frontend route `/trust-calibration` with summary cards, metrics table, recommendation panel, and run history
- no auto-apply, no real-money execution, no real routing

### Policy tuning board / recommendation-to-approval workflow (new)

The platform now includes a formal `policy_tuning` layer that turns trust calibration recommendations into explicit, auditable policy change candidates.

- recommendation source remains `trust_calibration`
- operational policy authority remains `automation_policy`
- new explicit flow: candidate -> review decision -> manual apply -> application log
- before/after snapshots persisted for traceability
- frontend board available at `/policy-tuning`

Still out of scope:
- auto-apply without approval
- real money
- real execution
- opaque planners / black-box learning
- complex multi-user governance


### Autonomy stage manager / domain-level envelopes (new)

The stack now includes `autonomy_manager` as a conservative domain-level governance layer above action-level policy tuning:

- groups related action types into auditable operational domains
- tracks explicit domain stages (`MANUAL`, `ASSISTED`, `SUPERVISED_AUTOPILOT`, `FROZEN`, `ROLLBACK_RECOMMENDED`)
- consolidates evidence from trust calibration, policy rollout, incidents, approval friction, and certification posture
- emits recommendation-first domain transitions
- keeps stage changes manual-first with explicit apply/rollback and approval-center integration for higher-impact changes

Scope stays unchanged: local-first, single-user, paper/sandbox only, no real-money execution, and no opaque auto-promotion planner.

### Autonomy rollout board / domain transition baselining (new)

A dedicated `autonomy_rollout` layer now closes the post-change loop for domain stage transitions:

- starts monitoring from an **already APPLIED** autonomy transition
- captures explicit baseline and post-change snapshots per domain
- compares before/after deltas for approvals, friction, blocked actions, incidents, and degraded context
- emits recommendation-first outcomes:
  - `KEEP_STAGE`
  - `REQUIRE_MORE_DATA`
  - `FREEZE_DOMAIN`
  - `ROLLBACK_STAGE`
  - `REVIEW_MANUALLY`
  - `STABILIZE_AND_MONITOR`
- supports auditable **manual rollback only**, optionally approval-gated
- includes conservative cross-domain warning notes when related incident/degraded signals are detected

Scope remains local-first and paper/sandbox only: no real money, no real execution, no silent auto-rollback.

### Autonomy roadmap board (new)

A new `autonomy_roadmap` layer now governs **cross-domain autonomy progression** as a staged portfolio (not just per-domain transitions):

- explicit dependency mapping between autonomy domains (`requires_stable`, `blocks_if_degraded`, `recommended_before`, `incompatible_parallel`)
- recommendation-first roadmap plans with blocked/frozen domains, sequence suggestions, and optional bundles
- strict manual-first boundary: no automatic multi-domain promotion or hidden planner behavior
- cockpit and autonomy pages now link to `/autonomy-roadmap` for global roadmap visibility

Key API surface:
- `GET /api/autonomy-roadmap/dependencies/`
- `POST /api/autonomy-roadmap/run-plan/`
- `GET /api/autonomy-roadmap/plans/`
- `GET /api/autonomy-roadmap/plans/<id>/`
- `GET /api/autonomy-roadmap/recommendations/`
- `GET /api/autonomy-roadmap/summary/`

Still out of scope:
- real-money flows
- real execution
- opaque automatic multi-domain promotion


### Autonomy scenario lab (new)

A new `autonomy_scenario` layer adds a **roadmap simulation / bundle what-if evaluator** on top of existing autonomy governance:

- compares scenario options (single domain, sequence, bundle, freeze+promote, delay-until-stable)
- estimates dependency conflict risk, approval friction, degraded/incident exposure, rollback hints, and approval-heavy posture
- persists auditable simulation runs (`AutonomyScenarioRun`) with per-option risk and recommendation records
- emits recommendation-first outcomes such as `BEST_NEXT_MOVE`, `SAFE_BUNDLE`, `SEQUENCE_FIRST`, `DELAY_UNTIL_STABLE`, `DO_NOT_EXECUTE`, and `REQUIRE_APPROVAL_HEAVY`

Hard boundaries remain unchanged: manual-first, simulation-only, paper/sandbox only, no real-money or real-execution paths, and no auto-apply.


### Autonomy campaign board / staged transition program (new)

The platform now includes `autonomy_campaign` as the formal handoff layer between roadmap/scenario recommendations and staged manual-first execution programs.

- source binding: roadmap plan, scenario run, or manual bundle
- wave/step/checkpoint model for transparent staged execution
- explicit controls: create/start/resume/abort
- approval-center checkpoint integration and resume-after-approval
- rollout monitor + observation checkpoint orchestration (without duplicating autonomy_rollout)
- cockpit and frontend route integration at `/autonomy-campaigns`

Explicit non-goals remain: no real money, no real execution, no opaque auto-promotion planner.

### Autonomy program control tower / campaign concurrency guard (new)

The stack now includes an explicit **program-level governance layer** for autonomy campaigns:

- backend app: `apps/backend/apps/autonomy_program`
- frontend route: `/autonomy-program`
- purpose: coordinate multiple autonomy campaigns safely as one program (not isolated runs)

What it adds:
- global program posture (`NORMAL`, `CONSTRAINED`, `HIGH_RISK`, `FROZEN`)
- explicit concurrency rules (`max_active_campaigns`, `incompatible_domains`, degraded/incident/observation blocks)
- campaign health snapshots (checkpoints, approvals, rollout warnings, incident/degraded impact)
- recommendations (`PAUSE_CAMPAIGN`, `REORDER_QUEUE`, `HOLD_NEW_CAMPAIGNS`, etc.)
- optional pause gating with approval-center handoff

What it does **not** add:
- real-money trading
- real execution
- opaque multi-campaign mass auto-orchestration
- black-box planner behavior

### Autonomy scheduler / campaign admission board (new)

A dedicated `autonomy_scheduler` layer now governs **pending campaign admission** into the autonomy program:

- explicit campaign admission queue and statuses (`PENDING`, `READY`, `DEFERRED`, `BLOCKED`, `ADMITTED`, `EXPIRED`)
- formal safe-start windows (`OPEN`, `UPCOMING`, `CLOSED`, `FROZEN`) with capacity and posture/domain constraints
- auditable scheduler planning runs + recommendation records
- recommendation-first actions (`SAFE_TO_ADMIT_NEXT`, `WAIT_FOR_WINDOW`, `BLOCK_ADMISSION`, `REORDER_ADMISSION_QUEUE`, `REQUIRE_APPROVAL_TO_ADMIT`)
- manual-first controls for admit/defer (no mass auto-start)

This module is intentionally adjacent to existing autonomy layers:
- `autonomy_campaign`: still owns campaign execution internals
- `autonomy_program`: still owns active campaign coexistence posture/rules
- `autonomy_scheduler`: now owns candidate admission ordering and safe-start timing

Still out of scope: real-money execution, real broker routing, distributed schedulers, opaque planners, multi-user orchestration.


### Autonomy launch control / preflight start gate (new)

A new `autonomy_launch` layer now sits between `autonomy_scheduler` admission and `autonomy_campaign` start:

- evaluates admitted/ready campaigns for **start-now readiness** under explicit preflight checks
- persists auditable `LaunchReadinessSnapshot`, `LaunchAuthorization`, `LaunchRun`, and `LaunchRecommendation` records
- blocks unsafe starts when posture/window/incidents/degraded/rollout pressure/checkpoints/approvals are not safe
- keeps a manual-first loop with explicit `authorize` / `hold` actions
- powers a new operator board at `/autonomy-launch` for readiness, blockers, recommendations, and authorization state

Scope remains unchanged: local-first, single-user, paper/sandbox only, and no opaque mass auto-start orchestration.

### Autonomy activation gateway / authorized start handoff (new)

A new `autonomy_activation` layer now sits after `autonomy_launch` authorization and before `autonomy_campaign.start`.

What it adds:
- consumes `LaunchAuthorization(AUTHORIZED)` records
- revalidates posture/window/conflicts/incidents at actual dispatch time
- executes explicit, auditable manual dispatch into campaign start
- records activation outcomes (`STARTED`, `BLOCKED`, `FAILED`, `EXPIRED`)
- emits dispatch recommendations and run summaries for cockpit/trace visibility

What it does **not** add:
- real-money/live broker execution
- opaque mass auto-start
- distributed scheduler orchestration
- multi-user enterprise workflow

### Autonomy operations monitor / active campaign runtime board (new)

The platform now includes a formal `autonomy_operations` layer for **active campaign runtime supervision**.

What it adds:
- runtime snapshots for started campaigns (wave/step/checkpoint/progress/stall pressure)
- explicit operational attention signals (`OPEN`/`ACKNOWLEDGED`)
- auditable monitor runs and recommendation outputs (`CONTINUE`, `PAUSE`, `ESCALATE`, `REVIEW_FOR_ABORT`, etc.)
- new operator route `/autonomy-operations` integrated with activation/campaign/approvals/trace/cockpit

What it does not change:
- `autonomy_campaign` remains execution authority
- `autonomy_activation` remains dispatch/start authority
- `autonomy_program` remains global posture authority

Scope remains local-first, single-user, paper/sandbox only, with manual-first controls and no opaque auto-remediation.


### Autonomy intervention control / manual remediation gateway (new)

A new `autonomy_intervention` layer now formalizes **manual-first interventions** on active autonomy campaigns:

- auditable `CampaignInterventionRequest`, `CampaignInterventionAction`, `InterventionRun`, and `InterventionOutcome`
- explicit actions: pause, resume, escalate-to-approval, review-for-abort, clear-to-continue
- policy validation against campaign terminal state, runtime blockers, incident pressure, and program frozen posture
- approval-center integration for sensitive interventions
- dedicated backend API under `/api/autonomy-interventions/*` and frontend board at `/autonomy-interventions`

Still out of scope: real money, real broker/exchange execution, opaque auto-remediation, and multi-user orchestration.

### Autonomy recovery board / paused campaign resolution (new)

The stack now includes a formal `autonomy_recovery` governance layer for campaigns that are paused, blocked, escalated, or pending disposition after intervention:

- candidate discovery for paused/blocked/recently intervened campaigns
- explicit blocker consolidation (approvals/checkpoints/incidents/program posture/domain locks)
- auditable recovery snapshots + runs + recommendations
- conservative recommendations: keep paused, resume-ready, require more recovery, review-for-abort, close-candidate, and recovery-priority reorder
- manual-first approval hooks for sensitive resume/close decisions
- frontend route `/autonomy-recovery` for operator review and traceable next actions

Scope remains unchanged: local-first, single-user, paper/sandbox only, with no real broker/exchange execution and no opaque auto-recovery.


### Autonomy disposition board / campaign closure committee (new)

The platform now includes a formal `autonomy_disposition` governance layer for final campaign lifecycle disposition:

- consolidates campaigns that are ready to close, abort, retire, or remain open
- records auditable `CampaignDisposition` outcomes with rationale, blockers, and before/after state
- generates disposition runs + recommendations and supports approval-center gating for sensitive actions
- exposes a dedicated UI route at `/autonomy-disposition` for manual-first review and apply

This layer consumes recovery/intervention/operations context and does **not** replace campaign execution, recovery evaluation, or program posture authority. Scope remains local-first, single-user, and paper/sandbox only.


### Autonomy closeout board / campaign archive dossier (new)

The platform now includes `autonomy_closeout`, a post-disposition governance layer that converts final campaign outcomes into auditable closeout dossiers and reusable learning handoffs:

- consolidates post-disposition closeout candidates with explicit ready/blocked posture
- persists `CampaignCloseoutReport`, `CloseoutFinding`, `CloseoutRun`, and `CloseoutRecommendation`
- derives structured lifecycle/blocker/incident/intervention/recovery summaries
- emits explicit handoff stubs for `memory_retrieval`, `postmortem-board`, and roadmap/scenario feedback
- keeps completion manual-first (`POST /api/autonomy-closeout/complete/<campaign_id>/`) with blocker/approval checks

Boundaries:
- does **not** replace `autonomy_disposition` as final disposition authority
- does **not** auto-archive, auto-learn opaquely, or auto-apply roadmap changes
- remains local-first, single-user, and paper/sandbox only

### Autonomy followup board (new)

The platform now adds a formal `autonomy_followup` layer that sits after `autonomy_closeout`:

- consumes closeout reports/findings/recommendation context (without replacing closeout)
- emits auditable manual-first handoffs to memory, postmortem request routing, and roadmap/scenario feedback stubs
- records followup history (`EMITTED`, `BLOCKED`, `DUPLICATE_SKIPPED`, etc.) and deduplicates repeated emissions
- provides `/autonomy-followup` UI + `/api/autonomy-followup/*` endpoints for candidates, run-review, summary, recommendations, and campaign emission

Still out of scope: real-money execution, broker/exchange live routing, opaque auto-learning, and auto-apply roadmap mutations.

### Autonomy feedback board / knowledge-loop completion governance (new)

A new `autonomy_feedback` layer now tracks *post-emission* follow-up resolution status for campaigns.

- `autonomy_followup` still emits handoffs (`EMITTED`, `DUPLICATE_SKIPPED`).
- `autonomy_feedback` consumes emitted follow-ups and tracks downstream status (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `REJECTED`, `UNKNOWN`).
- manual-first run endpoint creates auditable resolution records, recommendation records, and summary counts for closed-loop governance.
- frontend route `/autonomy-feedback` exposes summary cards, candidate/resolution tracking, recommendation queue, and manual completion action.

Out of scope remains unchanged: real money, real broker/exchange execution, opaque auto-learning, and automatic roadmap/scenario apply.

### Autonomy insights board (new)

Added a formal `autonomy_insights` layer to synthesize reusable lessons across **closed lifecycle campaigns** (`closeout + followup + feedback`).

Capabilities:
- manual-first cross-campaign synthesis runs (`/api/autonomy-insights/run-review/`)
- auditable `CampaignInsight`, `InsightRecommendation`, and `InsightRun` records
- explicit success/failure/blocker/governance pattern extraction (rule-based, no ML/LLM authority)
- recommendation targets for memory/roadmap/scenario/program/manager/operator review
- frontend board at `/autonomy-insights` connected to cockpit, closeout, followup, feedback, and trace

Boundaries remain unchanged: local-first, single-user, paper/sandbox only, no real broker/exchange execution, and no opaque auto-apply to roadmap/scenario/policy/runtime.


### Autonomy advisory resolution board (new)

A new `autonomy_advisory_resolution` layer closes the governance-note loop after `autonomy_advisory` emission:

- consumes emitted advisory artifacts and tracks explicit downstream statuses (`PENDING`, `ACKNOWLEDGED`, `ADOPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`)
- records auditable manual actions for acknowledge/adopt/defer/reject
- provides resolution runs, recommendation queue, and summary snapshots for cockpit/trace oriented operator review
- remains manual-first and recommendation-first (no opaque auto-apply to roadmap/scenario/program/manager)

Explicit non-goals remain unchanged: no real money, no broker/exchange execution, no black-box planner, and no multi-user enterprise orchestration.

### Autonomy backlog board / future-cycle planning handoff (new)

Added `autonomy_backlog` as a formal bridge between `autonomy_advisory_resolution` and future governance cycles.

What it adds:
- consumes `ADOPTED` / `ACKNOWLEDGED` advisory resolutions as backlog candidates
- creates auditable `GovernanceBacklogItem` records (roadmap/scenario/program/manager/operator_review targets)
- stores run and recommendation artifacts (`BacklogRun`, `BacklogRecommendation`) with explicit counts and rationale
- applies deterministic dedup + transparent priority heuristics (no ML and no black-box planner)
- keeps actions manual-first (`run-review`, `create`, `prioritize`, optional `defer`)

Hard boundaries:
- no auto-apply mutations to roadmap/scenario/program/manager
- no real-money execution and no live broker/exchange routing
- local-first, single-user, paper/sandbox only


## Autonomy intake board (new)

`autonomy_intake` adds a governed handoff between `autonomy_backlog` and planning surfaces.
It consumes READY/PRIORITIZED backlog items and emits auditable planning proposals (roadmap/scenario/program/manager/operator review) with manual-first controls and duplicate protection, without auto-applying downstream changes.
