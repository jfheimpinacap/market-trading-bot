# Semi-Autonomous Demo Mode

This app adds a **paper/demo-only** semi-autonomous layer.

## What it does

- Generates trade proposals from existing `proposal_engine` services.
- Uses existing risk + policy outcomes (no policy duplication).
- Classifies each proposal as:
  - auto executable,
  - approval required,
  - blocked.
- Runs safe auto-execution only for conservative BUY paper trades.
- Creates `PendingApproval` rows for manual review workflows.

## What it does NOT do

- No real-money execution.
- No exchange authentication.
- No autonomous background agent loop.
- No scheduler/workers/websockets.

## API

- `POST /api/semi-auto/evaluate/`
- `POST /api/semi-auto/run/`
- `GET /api/semi-auto/runs/`
- `GET /api/semi-auto/runs/<id>/`
- `GET /api/semi-auto/pending-approvals/`
- `POST /api/semi-auto/pending-approvals/<id>/approve/`
- `POST /api/semi-auto/pending-approvals/<id>/reject/`
- `GET /api/semi-auto/summary/`
