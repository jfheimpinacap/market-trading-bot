# Frontend architecture

## Purpose

The frontend is a local-first operator workspace for `market-trading-bot`. In the current phase it focuses on five responsibilities only:

1. provide a professional application shell
2. expose clear navigation for planned modules
3. surface minimal technical health from the backend
4. present a useful dashboard powered by real local demo data
5. provide a technical System page for inspecting local runtime context and observable simulation activity
6. provide a paper trading Portfolio page for inspecting the local demo account, positions, trades, and snapshots
7. provide a market-detail paper trading entry flow so a user can execute a local simulated trade directly from `/markets/:marketId`
8. surface demo signals and mock-agent output as a bridge between markets, paper trading, and future automation

This phase intentionally excludes authentication, real trading logic, market integrations, websockets, and advanced data visualization beyond a simple snapshot-based line chart in market detail.

## Structure

The frontend source tree is intentionally shallow and practical:

- `app/`: app composition and shared providers
- `components/`: reusable presentation building blocks, including dedicated dashboard, markets, and system UI
- `hooks/`: page-agnostic frontend behavior
- `layouts/`: app shell and persistent navigation structure
- `lib/`: static config and lightweight helpers
- `pages/`: route-level views
- `services/`: API requests and backend integration points
- `styles/`: global styling
- `types/`: shared UI and API types
- `store/`: reserved for future shared state if it becomes necessary

## Routing approach

The current frontend uses a lightweight browser-history router implemented in-app to keep dependencies minimal at this scaffold stage.

It supports:

- persistent layout shell
- sidebar navigation
- browser back/forward navigation
- route-specific topbar context
- simple not-found fallback

If the application later needs nested routing, URL params, or more advanced route guards, this can be upgraded to React Router without changing the page and layout boundaries introduced in this phase.

## Shared system health state

The frontend fetches `GET /api/health/` through a small service layer and shares the result through a provider in `src/app/`.

Why this approach:

- avoids duplicated fetch logic between Dashboard and System
- keeps the service boundary explicit
- avoids introducing a heavier client-state library too early
- preserves a clean place for future refresh policies or polling

## Data integration strategy

The current UI deliberately reuses a small set of fetch primitives instead of introducing route-specific data infrastructure.

### Dashboard

The home route composes three existing frontend primitives:

- `useSystemHealth` for shared health visibility
- `services/markets.ts` for catalog summary and recent market requests
- `DataStateWrapper` for section-level loading, error, and empty states

### System page

The `/system` route follows the same rule set:

- reuses `useSystemHealth` for backend status
- reuses `getMarketSystemSummary()` for catalog totals
- reuses `getMarkets()` for activity inference
- compares current and previous successful responses in-page to infer local simulation movement
- avoids new endpoints, polling infrastructure, websocket wiring, or operational controls

This keeps the System page technical and useful while preserving the local-first architecture.


### Signals page and integrations

The `/signals` route now follows the same local-first strategy:

- uses `services/signals.ts` as the single integration point for the signals API
- keeps contracts in `types/signals.ts`
- loads summary, agent registry, and filtered signal rows without introducing a parallel client or global state library
- reuses existing `PageHeader`, `SectionCard`, `DashboardStatGrid`, `DataStateWrapper`, and table styling patterns
- exposes a compact latest-signals block on the dashboard and a market-scoped signals section inside `/markets/:marketId`

This keeps signals understandable as a demo insight queue instead of prematurely building a complex analyst workstation.

### Portfolio page

The `/portfolio` route extends the same local-first pattern without introducing new client infrastructure:

- uses `services/paperTrading.ts` as the single integration point for paper trading endpoints
- keeps shared TypeScript contracts in `types/paperTrading.ts`
- loads account, summary, positions, trades, and snapshots in parallel with section-level error isolation
- supports manual portfolio revaluation through `POST /api/paper/revalue/` followed by a full refresh of visible sections
- reuses existing shell, `PageHeader`, `SectionCard`, `DataStateWrapper`, and table styling patterns instead of inventing a new visual system

This keeps the Portfolio page useful for operators while still avoiding trading forms, streaming updates, and heavier state-management dependencies.

### Market detail paper trading and history

The `/markets/:marketId` route now extends the same pattern to support both a lightweight historical view and the first actionable paper trading flow:

- reuses `GET /api/markets/<id>/` as the single source for market header data, rules, metadata, recent snapshots, and the simple history chart
- maps `recent_snapshots` into a typed frontend dataset instead of adding a dedicated chart endpoint
- renders a sober SVG line chart with `market_probability` as the primary series and optional `yes_price` / `no_price` overlays when the snapshot payload includes them
- keeps the chart intentionally lightweight: fixed normalized 0%–100% scale, simple tooltip, no streaming updates, no range selector, and no charting dependency
- reuses `services/paperTrading.ts` instead of introducing a second API client
- executes demo trades through `POST /api/paper/trades/`
- reads `GET /api/paper/account/`, `GET /api/paper/summary/`, `GET /api/paper/positions/`, and `GET /api/paper/trades/` to render account context and current exposure for that market
- triggers `POST /api/paper/revalue/` after a successful execution and then refreshes the market-local paper context
- keeps the UX intentionally simple: trade type, side, quantity, estimated cost, visible result state, and a link to `/portfolio`
- avoids websockets, global client state, exchange-style order books, and advanced order-entry concepts

This keeps market detail actionable without turning the current frontend into a heavy trading terminal.

## UI principles for this stage

- sober, readable visual design
- consistent panels and typography
- responsive layout without overengineering
- placeholders that explain purpose instead of empty screens
- local-first configuration visibility
- real data in the dashboard and system panel before introducing advanced analytics
- section-level failure isolation so one broken endpoint does not collapse the entire page
- market-local actionability: when a route becomes interactive, keep the control surface near the read context it depends on
- signals should read as explicit demo heuristics, not as implied real financial intelligence or autonomous advice

## Planned evolution

Near-term frontend evolution can proceed without reworking the shell:

- expand technical system panels when backend diagnostics grow
- expose richer provider and worker diagnostics
- connect backend modules beyond healthcheck and market summary
- add local settings forms
- introduce richer routing only when it provides clear value
- expand the Portfolio page from read-only visibility into controlled paper trade entry flows once UX requirements are clear
- prepare lightweight summaries for Agents and Post-Mortem once backend endpoints exist
- consider optional lightweight auto-refresh for local simulation monitoring if manual refresh becomes limiting
