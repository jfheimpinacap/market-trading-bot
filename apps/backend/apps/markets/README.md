# Markets app

The `apps.markets` Django app contains the provider-agnostic prediction-market catalog used by the local-first backend.

## Purpose of the current stage
This stage keeps the domain intentionally simple while making it useful for local development:
- load coherent demo providers, events, markets, snapshots, and rules
- inspect that catalog comfortably in Django admin
- expose read-only API endpoints that the frontend can consume immediately
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
- filters, search, ordering, and market detail snapshots/rules

## Intentionally out of scope
Still not implemented in this stage:
- real provider integrations
- sync jobs or ingestion tasks
- websocket feeds
- paper trading
- orders, positions, fills, or portfolio logic
- signals, risk, or machine learning
- advanced auth flows
