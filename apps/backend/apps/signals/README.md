# Signals app

`apps.signals` adds the first local-first demo layer for opportunities, recommendations, and simulated insights on top of the existing market catalog.

## What this app does now

- creates a small registry of **mock agents** such as `scan-agent`, `prediction-agent`, and `risk-agent`
- generates **demo market signals** using explicit local heuristics only
- stores **signal runs** so the system can trace each local generation pass
- exposes read-only API endpoints for the frontend `/signals` page and market-detail integrations
- keeps admin surfaces useful without introducing real autonomous agents, external providers, or ML

## What this app does not do yet

- no real LLM orchestration
- no scrapers or external research
- no real provider integrations
- no machine-learning models
- no auto-trading or execution decisions
- no sophisticated risk engine

## Main models

- `MockAgent`: a demo analysis role such as scan, research, prediction, risk, or postmortem
- `MarketSignal`: a scored and explainable demo signal linked to one market and optionally one agent
- `SignalRun`: a record of each local signal-generation pass

## Local heuristics used now

The current heuristics are intentionally simple and explicit:

- compare `current_market_probability` against a local baseline from recent snapshots
- look for fast moves across the recent snapshot window
- flag extreme probabilities as interesting or stretched
- reduce actionability when spread is wide, activity is thin, or the market is paused/terminal
- use deterministic score/confidence formulas so behavior is reproducible and explainable

These heuristics are **demo-only** and should not be interpreted as real financial advice or forecasting quality.

## Management commands

Seed mock agents:

```bash
cd apps/backend
python manage.py seed_mock_agents
```

Generate demo signals:

```bash
cd apps/backend
python manage.py generate_demo_signals
```

Useful options:

```bash
python manage.py generate_demo_signals --limit 5
python manage.py generate_demo_signals --market-id 3
python manage.py generate_demo_signals --clear-existing
```

## API endpoints

- `GET /api/signals/`
- `GET /api/signals/<id>/`
- `GET /api/signals/agents/`
- `GET /api/signals/summary/`

Supported list filters:

- `market`
- `agent`
- `signal_type`
- `status`
- `direction`
- `is_actionable`
- `ordering` with `created_at`, `score`, or `confidence`

## Relationship to other apps

- builds on `apps.markets` as the source of current market fields and historical snapshots
- complements `apps.paper_trading` by surfacing demo ideas before a user chooses to place a paper trade
- stays local-first and demo-only so future agent architecture can evolve without rewriting these boundaries


## Signal fusion / opportunity board (new)

Besides legacy demo `MarketSignal` heuristics, this app now includes a formal paper/demo-only fusion layer:

- `SignalFusionRun`: one auditable fusion pass across research + prediction + risk (+ runtime/safety context)
- `OpportunitySignal`: composite per-market output with score, rank, status and rationale
- `ProposalGateDecision`: explicit pre-proposal gate (`should_generate_proposal`, `proposal_priority`, `blocked_reason`)

Statuses are intentionally simple:
- `WATCH`
- `CANDIDATE`
- `PROPOSAL_READY`
- `BLOCKED`

Signal profiles are explicit and configurable in code:
- `conservative_signal`
- `balanced_signal`
- `aggressive_light_signal`

### New API endpoints

- `POST /api/signals/run-fusion/`
- `GET /api/signals/runs/`
- `GET /api/signals/runs/<id>/`
- `GET /api/signals/opportunities/`
- `GET /api/signals/board-summary/`
- `POST /api/signals/run-to-proposal/`

### Scope boundaries (still enforced)

- local-first, paper/demo only
- no real money
- no real order execution
- no opaque planner/optimizer
- no LLM authority for final trade decisions
