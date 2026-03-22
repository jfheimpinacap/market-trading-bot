# Frontend architecture

## Purpose

The frontend is a local-first operator workspace for `market-trading-bot`. In the current phase it focuses on four responsibilities only:

1. provide a professional application shell
2. expose clear navigation for planned modules
3. surface minimal technical health from the backend
4. present a useful dashboard powered by real local demo data

This phase intentionally excludes authentication, real trading logic, market integrations, websockets, and advanced data visualization.

## Structure

The frontend source tree is intentionally shallow and practical:

- `app/`: app composition and shared providers
- `components/`: reusable presentation building blocks, including dedicated dashboard and markets UI
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

## Dashboard integration strategy

The home route now composes three existing frontend primitives instead of creating a parallel architecture:

- `useSystemHealth` for shared health visibility
- `services/markets.ts` for catalog summary and recent market requests
- `DataStateWrapper` for section-level loading, error, and empty states

This keeps the dashboard robust even when one backend request fails and another still succeeds.

## UI principles for this stage

- sober, readable visual design
- consistent panels and typography
- responsive layout without overengineering
- placeholders that explain purpose instead of empty screens
- local-first configuration visibility
- real data in the dashboard before introducing advanced analytics

## Planned evolution

Near-term frontend evolution can proceed without reworking the shell:

- expand technical system panels
- expose richer provider and worker diagnostics
- connect backend modules beyond healthcheck and market summary
- add local settings forms
- introduce richer routing only when it provides clear value
- prepare lightweight summaries for Portfolio, Agents, and Post-Mortem once backend endpoints exist
