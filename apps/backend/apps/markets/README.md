# Markets app

The `apps.markets` Django app contains the provider-agnostic prediction-market catalog used by the local-first backend.

## Purpose of the current stage
This stage keeps the domain intentionally simple while making it useful for local development:
- load coherent demo providers, events, markets, snapshots, and rules
- inspect that catalog comfortably in Django admin
- expose read-only API endpoints that the frontend can consume immediately
- simulate live-looking market activity locally without real provider integrations or trading
- stay provider-agnostic without real Kalshi or Polymarket integrations

## Models

### Provider
Represents a market source such as a demo Kalshi-like or Polymarket-like catalog.

Key fields:
- `name`
- `slug`
- `description`
- `is_active`
- `base_url`
- `api_base_url`
- `notes`

### Event
Represents a provider-level grouping such as an election, macroeconomic release, sports final, or technology launch window.

Key fields:
- `provider`
- `provider_event_id`
- `title`
- `slug`
- `category`
- `status`
- `open_time`
- `close_time`
- `resolution_time`
- `metadata`

### Market
Represents a specific prediction market that can later be analyzed, snapshotted, or displayed in the frontend.

Key fields:
- `provider`
- `event`
- `provider_market_id`
- `ticker`
- `title`
- `slug`
- `category`
- `market_type`
- `outcome_type`
- `status`
- `resolution_source`
- `short_rules`
- `url`
- `is_active`
- `open_time`
- `close_time`
- `resolution_time`
- `current_market_probability`
- `current_yes_price`
- `current_no_price`
- `liquidity`
- `volume_24h`
- `volume_total`
- `spread_bps`
- `metadata`

### MarketSnapshot
Represents a historical snapshot of a market at a specific point in time.

Key fields:
- `market`
- `captured_at`
- `market_probability`
- `yes_price`
- `no_price`
- `last_price`
- `bid`
- `ask`
- `spread`
- `liquidity`
- `volume`
- `volume_24h`
- `open_interest`
- `metadata`

### MarketRule
Stores longer-form market rules or resolution guidance separately from the main `Market` row.

Key fields:
- `market`
- `source_type`
- `rule_text`
- `resolution_criteria`

## Relationship overview
- A `Provider` has many `Event` rows.
- A `Provider` has many `Market` rows.
- An `Event` groups related markets from one provider.
- A `Market` may be linked to an `Event`, but the model stays flexible enough for staged ingestion later.
- A `Market` has many `MarketSnapshot` rows for historical analysis.
- A `Market` has zero or more `MarketRule` rows for rule provenance and detail views.

## Demo seed workflow
A reusable management command is available to populate a realistic local catalog:

```bash
cd apps/backend
python manage.py seed_markets_demo
```

### What the seed creates
The seed is deterministic and safe to run multiple times because it updates-or-creates rows using provider and slug identities.

It currently creates:
- 2 demo providers: `kalshi` and `polymarket`
- 6 events across politics, economics, sports, technology, and geopolitics
- 12 markets with mixed statuses such as `open`, `paused`, `closed`, `resolved`, and `cancelled`
- 72 snapshots total, with 6 time-series points per market
- 6 rule records for selected markets

### Demo data design
The seeded data is intentionally fictitious but realistic enough for development:
- coherent timestamps
- yes/no prices derived from market probabilities
- recent snapshot evolution for charts or sparklines
- active and inactive markets
- terminal states for detail and badge rendering
- varied categories for filters and navigation

## Local simulation engine
The app now includes a small simulation layer under `apps/markets/simulation/`.

Current modules:
- `simulation/utils.py`: quantization, clamping, price derivation, and order-book helpers
- `simulation/rules.py`: market eligibility, volatility scaling, time-pressure drift, and conservative status-transition rules
- `simulation/engine.py`: orchestration that updates eligible demo markets and creates aligned `MarketSnapshot` rows

### Simulation goals
The simulation is intentionally simple and local-first:
- only acts on demo markets already stored in the database
- keeps prices/probabilities/liquidity/volume moving in small, bounded steps
- skips terminal markets such as `resolved`, `cancelled`, and `archived`
- treats `open`, `paused`, and `closed` differently
- creates a new snapshot for each market that changes on a tick
- does not introduce trading logic, provider sync, ML, or websockets

### Fields updated by simulation
A successful tick can update:
- `current_market_probability`
- `current_yes_price`
- `current_no_price`
- `liquidity`
- `volume_24h`
- `volume_total`
- `spread_bps`
- `status`
- `is_active`
- `metadata["simulation"]`

A matching `MarketSnapshot` is created with aligned probability, prices, spread, liquidity, total volume, and `captured_at`.

### Movement rules
The movement logic is intentionally legible instead of mathematically complex:
- probabilities are clamped between `0.0100` and `0.9900`
- yes/no prices are re-derived from probability on every tick
- volatility is slightly different by category
- markets closer to `resolution_time` can move a bit more
- paused markets move far less than open markets
- closed markets barely move and primarily exist to carry final pre-resolution state forward
- spread stays non-negative and bounded
- liquidity never goes negative
- `volume_total` never decreases

### Status transitions simulated today
Status changes are conservative and intentionally rare:
- `open -> paused` occasionally
- `paused -> open` occasionally
- `open -> closed` when `close_time` is reached, or very rarely near the close window
- `closed -> resolved` when `resolution_time` is reached, or very rarely close to that window

The engine does **not** attempt to simulate every lifecycle path or infer real outcomes.

## Simulation commands

### Manual tick
Run a single tick:

```bash
cd apps/backend
python manage.py simulate_markets_tick
```

Useful options:

```bash
python manage.py simulate_markets_tick --dry-run
python manage.py simulate_markets_tick --limit 5
python manage.py simulate_markets_tick --seed 7
```

The command prints a development-oriented summary including:
- markets processed
- markets updated
- markets skipped
- snapshots created
- any status changes
- per-market probability movement for updated rows

### Local loop mode
Run a simple local loop that applies repeated ticks:

```bash
cd apps/backend
python manage.py simulate_markets_loop --interval 10 --iterations 20
```

Continuous mode is also supported:

```bash
python manage.py simulate_markets_loop --interval 5
```

Stop continuous mode with `Ctrl+C`.

Useful loop options:
- `--interval <seconds>`
- `--iterations <count>`
- `--limit <count>`
- `--dry-run`
- `--seed <int>`

## Admin improvements
The Django admin is intended to be practical for local inspection.

### Provider admin
- event and market counts in the list view
- search by name, slug, and description

### Event admin
- provider/category/status filters
- market count per event
- readonly timestamps and slug for safer inspection

### Market admin
- quick visibility of provider, linked event, status, probability, liquidity, and snapshot counts
- simple actions to mark selected markets active or inactive
- inline market rules
- inline recent snapshots limited to the latest 5 rows
- readonly operational fields such as timestamps, slug, provider market id, and snapshot summary data
- last simulation tick visible from market metadata once a tick has run

### Snapshot and rule admin
- provider visible directly in list tables
- more useful select-related query behavior for local admin browsing

## API surface
Read-only endpoints currently exposed under `/api/markets/`:
- `GET /api/markets/providers/`
- `GET /api/markets/events/`
- `GET /api/markets/`
- `GET /api/markets/<id>/`
- `GET /api/markets/system-summary/`

No new API endpoints are required for simulation. The frontend can see changes by refreshing the existing endpoints.

### Provider response
Provider list responses include lightweight aggregate counts:
- `event_count`
- `market_count`

### Event list response
The event list stays compact and includes:
- provider summary
- key timing/status fields
- `market_count`

Supported filters on `GET /api/markets/events/`:
- `provider=<provider-slug>`
- `status=<event-status>`
- `category=<category>`

### Market list response
The market list is intentionally light for catalog pages and cards.

Included highlights:
- provider summary
- `event_id`
- `event_title`
- current probability and price fields
- liquidity and volume metrics
- `snapshot_count`
- `latest_snapshot_at`

Supported filters on `GET /api/markets/`:
- `provider=<provider-slug>`
- `category=<category>`
- `status=<market-status>`
- `is_active=true|false`
- `event=<event-id>`
- `search=<text>` on market title

Supported ordering on `GET /api/markets/`:
- `ordering=title`
- `ordering=created_at`
- `ordering=resolution_time`
- `ordering=current_market_probability`
- `ordering=liquidity`
- `ordering=volume_24h`

Prefix any ordering field with `-` for descending order.

### Market detail response
The market detail serializer is richer than the list serializer and includes:
- nested event detail
- full `short_rules`
- `metadata`
- all related `rules`
- `recent_snapshots` limited to the latest 5 snapshots

### System summary response
`GET /api/markets/system-summary/` returns lightweight counts useful for a local dashboard or home page:
- `total_providers`
- `total_events`
- `total_markets`
- `active_markets`
- `resolved_markets`
- `total_snapshots`

## Local verification flow
A practical local flow for this stage is:

```bash
cd apps/backend
python manage.py migrate
python manage.py seed_markets_demo
python manage.py simulate_markets_tick
python manage.py runserver
```

Or, for continuous local activity:

```bash
cd apps/backend
python manage.py migrate
python manage.py seed_markets_demo
python manage.py simulate_markets_loop --interval 10
python manage.py runserver
```

### How to verify simulation worked
- Open Django admin and inspect a market's `Last simulation tick` plus recent snapshots.
- Open `/api/markets/` and confirm `current_market_probability`, `liquidity`, `volume_24h`, `volume_total`, and `latest_snapshot_at` change.
- Open `/api/markets/<id>/` and confirm `recent_snapshots` includes the newest simulated row.
- Open `/api/markets/system-summary/` and confirm `total_snapshots` increases after each live tick.

## Limitations of this stage
This stage intentionally does **not** include:
- provider integrations
- real market sync jobs
- websockets
- trading workflows
- orders, fills, positions, or portfolio accounting
- signals or agents
- ML or forecasting
- advanced charts or dashboards

## Testing
Run market tests with the dedicated test settings:

```bash
cd apps/backend
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps.markets
```

Current coverage includes:
- demo seed creation
- seed idempotence
- management command output
- provider/event/market/system-summary endpoints
- simulation tick persistence
- snapshot creation
- value bounds for simulated fields
- dry-run behavior
- loop command iterations
