# Codex collaboration notes

This folder is reserved for prompt templates, implementation briefs, and reusable task definitions for future Codex-assisted work.

## Suggested guidelines for future tasks

- Keep each task narrowly scoped to one architectural concern.
- Reference the target module explicitly (`apps`, `services`, `libs`, `infra`, or `docs`).
- Avoid requesting multiple business domains in a single step when a scaffold or interface-first iteration is enough.
- Ask for validations (tests, checks, commands) alongside code changes.
- Prefer incremental additions over premature business logic.

## Expected next steps

- Define API contracts for core backend modules.
- Add frontend routing and feature-specific slices only when requirements are stable.
- Introduce provider interfaces before implementing venue-specific integrations.
