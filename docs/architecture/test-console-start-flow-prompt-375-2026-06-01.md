# Prompt 375 – Test Console start confirmation contract

This note documents the Operational Test Console start flow fix for the case where the UI remained on `Starting...` while the backend only showed the CORS preflight request.

## State distinctions

- **Preflight OPTIONS OK**: the browser has asked whether `POST /api/mission-control/test-console/start/` is allowed. This does **not** mean the Test Console start handler ran, and it does not create a run.
- **POST start received**: the backend view/service received the real start request. The backend logs this with `[test-console] start-request-received`.
- **Start confirmed**: the backend accepted the POST, logs `[test-console] start-accepted`, and exposes an active run identity through `active_run`/`has_active_run` plus `current_run_id`/`run_id`.
- **Start failed**: the POST returned an HTTP error or the browser request failed. The UI must show `Start failed`, the HTTP status when available, and the backend message when available; the Start button is re-enabled.
- **Start not confirmed**: after a short confirmation window, status still reports backend idle (`NO_RUN_YET`/`IDLE`, `phase=idle`, no active run, and no run id). The UI shows `Start not confirmed · backend still idle · no POST/start event received` and re-enables Start.

## Operational checks

Manual validation should use DevTools > Network and backend logs together:

1. Click **Run selected profile**.
2. Confirm the network panel shows both `OPTIONS /api/mission-control/test-console/start/` and `POST /api/mission-control/test-console/start/`.
3. Confirm backend logs include `[test-console] start-request-received` and then either `[test-console] start-accepted` or `[test-console] start-rejected`.
4. Confirm the UI moves from `Start requested` to `Start confirmed`/`Running` and displays `current_run_id` with an active backend run.

This change is limited to the Test Console frontend/backend start contract and does not modify trading policy, risk decisions, execution/trade paths, LLM, or training behavior.
