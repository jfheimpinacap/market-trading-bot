# Paper trading app

`apps.paper_trading` adds the first backend-only domain for local-first demo investing with imaginary money. It is intentionally simple: no broker integrations, no real execution, no matching engine, and no multi-user portfolio complexity yet.

## Purpose
- provide a persistent demo paper account
- represent simulated positions and executed paper trades
- keep account-level cash, equity, and PnL values consistent
- reuse existing `apps.markets` pricing fields for immediate demo execution and mark-to-market
- expose admin tooling and basic DRF endpoints for the future frontend paper trading flow

## Models

### `PaperAccount`
Represents a virtual account balance.

Key fields:
- `name`, `slug`, `currency`
- `initial_balance`, `cash_balance`, `reserved_balance`
- `equity`, `realized_pnl`, `unrealized_pnl`, `total_pnl`
- `is_active`, `notes`

### `PaperPosition`
Represents the current simulated exposure for one `account + market + side`.

Key fields:
- `account`, `market`, `side`
- `quantity`, `average_entry_price`, `current_mark_price`
- `cost_basis`, `market_value`
- `realized_pnl`, `unrealized_pnl`
- `status`, `opened_at`, `closed_at`, `last_marked_at`

### `PaperTrade`
Represents an executed immediate paper trade.

Key fields:
- `account`, `market`, `position`
- `trade_type`, `side`, `quantity`, `price`
- `gross_amount`, `fees`, `status`
- `executed_at`, `notes`, `metadata`

### `PaperPortfolioSnapshot`
Stores account-level historical snapshots for later charts and portfolio history.

## Demo trading flow
1. Ensure the demo account exists with `seed_paper_account`.
2. POST a trade to `/api/paper/trades/` with `market_id`, `trade_type`, `side`, and `quantity`.
3. The execution service reads the current `Market` price:
   - `YES` uses `current_yes_price`, or derives a 0-100 demo price from `current_market_probability`
   - `NO` uses `current_no_price`, or derives the complementary 0-100 demo price
4. For `BUY`, the system checks cash balance and opens or increases the position.
5. For `SELL`, the system checks available quantity and reduces or closes the position.
6. The portfolio is revalued and a `PaperPortfolioSnapshot` is written.

## Services
- `services/execution.py`: immediate demo trade execution and account/position updates
- `services/valuation.py`: price resolution, market validation, mark-to-market, and account revaluation
- `services/portfolio.py`: ensure/get demo account, summary building, and snapshot creation

## Management commands
```bash
cd apps/backend
python manage.py seed_paper_account
python manage.py refresh_paper_portfolio
```

## API endpoints
- `GET /api/paper/account/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `POST /api/paper/trades/`
- `GET /api/paper/summary/`
- `POST /api/paper/revalue/`
- `GET /api/paper/snapshots/`

### Example trade request
```bash
curl -X POST http://localhost:8000/api/paper/trades/ \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": 1,
    "trade_type": "BUY",
    "side": "YES",
    "quantity": "10"
  }'
```

## What is implemented now
- one or more paper accounts, with a default demo account helper
- immediate paper buy/sell execution against current market prices
- open/closed positions with account-level realized and unrealized PnL
- account snapshots for future history views
- admin pages for accounts, positions, trades, and snapshots
- basic DRF endpoints and tests for the main demo flows

## Not implemented yet
- real money or broker/provider integrations
- multi-user auth and account ownership
- limit orders, order queues, or matching logic
- realistic fee schedules or risk controls
- websockets, live order streams, or automated strategies
