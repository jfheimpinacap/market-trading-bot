# Monorepo architecture

## Initial intent

This repository starts as a clean monorepo scaffold for a prediction markets intelligence platform. The goal of this phase is to establish clear boundaries between user-facing apps, backend APIs, future engines/services, shared libraries, infrastructure, and documentation.

## Top-level areas

- **`apps/`**: runnable products. Today it contains the React frontend and Django backend.
- **`services/`**: future domain engines such as discovery, pricing, risk, execution, and post-mortem analysis.
- **`libs/`**: reusable building blocks, especially provider adapters and cross-cutting utilities.
- **`infra/`**: local development infrastructure, automation scripts, and future deployment assets.
- **`docs/`**: architecture notes, API documentation, and prompt guidance for iterative development.

## Current application boundaries

### Frontend
- Built with React + Vite + TypeScript.
- Provides a minimal dashboard placeholder.
- Uses a scalable `src/` layout organized by app shell, pages, components, hooks, services, store, types, and styles.

### Backend
- Built with Django + Django REST Framework.
- Uses modular apps for `common`, `health`, `markets`, `agents`, and `audit`.
- Exposes a single healthcheck endpoint at `GET /api/health/`.
- Reads PostgreSQL and Redis/Celery settings from environment variables.

## Near-term evolution

- Add API modules gradually, keeping app boundaries explicit.
- Keep provider-specific logic inside `libs/provider-*` packages.
- Add worker or agent runtimes only after API contracts and module responsibilities are defined.
- Expand documentation and decision records as the project grows.
