# Markets app

The `apps.markets` Django app now contains the initial provider-agnostic market domain for prediction markets.

## Purpose
- Represent market providers without coupling the backend to a live provider integration.
- Store event and market catalog data in a way that works for future Kalshi, Polymarket, or other provider adapters.
- Preserve point-in-time market snapshots for historical analysis later.
- Keep the first version simple enough to inspect locally through Django admin and lightweight read-only API endpoints.

## Models

### Provider
Represents a market source such as Kalshi or Polymarket.

Key fields:
- `name`
- `slug`
- `description`
- `is_active`
- `base_url`
- `api_base_url`
- `notes`

### Event
Represents a provider-level grouping such as an election, macroeconomic release, or sports match.

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
Represents a specific prediction market that can later be analyzed, snapshotted, or paper-traded.

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

This was split into its own model to keep `Market` practical for catalog/listing use while still allowing multiple rule texts from different sources over time.

Key fields:
- `market`
- `source_type`
- `rule_text`
- `resolution_criteria`

## Relationship overview
- A `Provider` has many `Event` rows.
- A `Provider` has many `Market` rows.
- An `Event` can exist before any markets are loaded.
- A `Market` may be linked to an `Event`, but can remain temporarily unlinked if source data arrives in stages.
- A `Market` has many `MarketSnapshot` rows for historical analysis.
- A `Market` has zero or more `MarketRule` rows for rule provenance and future provider sync updates.

## API surface added in this iteration
Read-only endpoints were added to make the domain inspectable without introducing business workflows:
- `GET /api/markets/providers/`
- `GET /api/markets/events/`
- `GET /api/markets/`
- `GET /api/markets/<id>/`

## What is intentionally out of scope for now
- Real provider integrations
- Sync jobs or Celery ingestion flows
- Order books, orders, fills, or positions
- Paper trading
- Signals, risk, or portfolio logic
- WebSocket streaming
- Machine learning
- Authentication and permissions beyond the current simple local setup

## How this app can grow next
Future iterations can build on this base by adding:
- provider adapter ingestion into `Provider`, `Event`, and `Market`
- snapshot pipelines and scheduled sync jobs
- signal generation on top of `MarketSnapshot`
- paper trading models referencing `Market`
- richer metadata normalization once real providers are connected
