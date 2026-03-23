# Postmortem demo app

`apps.postmortem_demo` adds a local-first, explicitly mock trade review layer for executed paper trades. It closes the first review loop in the demo stack without pretending to be a professional analytics engine.

## Purpose
- review executed `PaperTrade` rows after the fact
- classify the current trade outcome as `FAVORABLE`, `NEUTRAL`, or `UNFAVORABLE`
- explain what happened after entry using deterministic local heuristics
- capture lightweight context from demo signals and risk assessments when available
- expose read-only API endpoints and admin screens for the frontend `/postmortem` workspace

## Model

### `TradeReview`
Stores one persisted post-trade review per paper trade.

Key fields:
- `paper_trade`, `paper_account`, `market`
- `review_status`
- `outcome`, `score`, `confidence`
- `summary`, `rationale`, `lesson`, `recommendation`
- `entry_price`, `current_market_price`, `price_delta`, `pnl_estimate`
- `market_probability_at_trade`, `market_probability_now`
- `signals_context`, `risk_decision_at_trade`, `metadata`
- `reviewed_at`, `created_at`, `updated_at`

## Demo review heuristics
The current implementation is intentionally simple and explainable.

It currently looks at:
- entry price versus the current market price for the traded side
- whether the trade was a `BUY` or `SELL`
- whether the latest signal before the trade was actionable and aligned with the trade side
- whether the associated risk assessment was `APPROVE`, `CAUTION`, or `BLOCK`
- whether the trade was relatively large for the paper account equity
- whether the market is now paused, closed, resolved, cancelled, or archived

Outcome classification today:
- favorable: signed move >= 3 price points
- neutral: signed move between -3 and +3 price points
- unfavorable: signed move <= -3 price points

This is a mock review engine only. It does **not** use ML, news, external providers, or advanced statistics.

## Service layer
- `services/review.py`: review generation orchestration and heuristic scoring

## Management command
Generate reviews locally:

```bash
cd apps/backend
python manage.py generate_trade_reviews
```

Useful options:

```bash
python manage.py generate_trade_reviews --limit 10
python manage.py generate_trade_reviews --trade-id 42
python manage.py generate_trade_reviews --refresh-existing
```

Without `--refresh-existing`, existing reviews are left in place. If the market changed after the last review, the existing review is marked `STALE`.

## API endpoints
- `GET /api/reviews/`
- `GET /api/reviews/<id>/`
- `GET /api/reviews/summary/`

Supported list filters:
- `trade` or `paper_trade`
- `market`
- `account` or `paper_account`
- `outcome`
- `review_status`
- `ordering=reviewed_at`, `ordering=-reviewed_at`, `ordering=score`, `ordering=created_at`

## Admin
The Django admin exposes `TradeReview` with useful filters, search fields, trade links, market links, and readable summary/lesson columns.

## Not implemented yet
- real post-mortem analytics or ML
- autonomous agents or external news analysis
- strategy adaptation or parameter tuning
- real-time review generation
- websocket updates or provider integrations
