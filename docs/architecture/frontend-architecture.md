# Frontend architecture

## Purpose

The frontend is a local-first operator workspace for `market-trading-bot`. In the current phase it focuses on three responsibilities only:

1. provide a professional application shell
2. expose clear navigation for planned modules
3. surface minimal technical health from the backend

This phase intentionally excludes authentication, real trading logic, market integrations, websockets, and advanced data visualization.

## Structure

The frontend source tree is intentionally shallow and practical:

- `app/`: app composition and shared providers
- `components/`: reusable presentation building blocks
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

## UI principles for this stage

- sober, readable visual design
- consistent panels and typography
- responsive layout without overengineering
- placeholders that explain purpose instead of empty screens
- local-first configuration visibility

## Planned evolution

Near-term frontend evolution can proceed without reworking the shell:

- add domain data cards and simple tables per page
- expand technical system panels
- add local settings forms
- connect backend modules beyond healthcheck
- introduce richer routing only when it provides clear value
