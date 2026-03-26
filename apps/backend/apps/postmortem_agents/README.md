# postmortem_agents

Structured **post-mortem board** for paper/demo-only trade loss review.

## What it does
- Runs a deterministic, auditable review committee per `TradeReview`.
- Generates perspective reviews: `narrative`, `prediction`, `risk`, `runtime`, `learning`.
- Produces a structured `PostmortemBoardConclusion` with failure modes and adjustments.
- Optionally creates a learning-memory entry + triggers conservative learning rebuild.

## What it does not do
- No real-money execution.
- No autonomous free-form planner.
- No opaque agent-to-agent chat loop.

## API
- `POST /api/postmortem-board/run/`
- `GET /api/postmortem-board/runs/`
- `GET /api/postmortem-board/runs/<id>/`
- `GET /api/postmortem-board/reviews/`
- `GET /api/postmortem-board/conclusions/`
- `GET /api/postmortem-board/summary/`

## Service layout
- `services/context.py`: gather structured evidence from existing modules.
- `services/reviewers.py`: perspective reviewers (LLM-local optional, graceful fallback).
- `services/conclusion.py`: board-level conclusion + learning handoff.
- `services/board.py`: orchestration of one board cycle.
