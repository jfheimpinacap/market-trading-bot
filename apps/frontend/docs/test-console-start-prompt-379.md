# Test Console fast ACK repair (Prompt 379)

Prompt 378 left the Test Console start path partially implemented: the code still executed the heavy bootstrap/scan/handoff/prediction/risk/execution/export pipeline inside `POST /api/mission-control/test-console/start/`, so the browser could wait until the request timed out or appeared cancelled.

Prompt 379 completes the split between the HTTP ACK and the background worker:

- `POST /api/mission-control/test-console/start/` validates the payload, resolves the selected/effective profile, creates a `tc-*` run id, stores an active `RUNNING` snapshot with `current_phase=queued`, and returns `202` immediately.
- The start ACK response should include `ok=true`, `active_run=true`, `run_id`, `current_run_id`, `active_run_detail`, `display_source=active_run`, `last_backend_event=start-ack-returned`, `next_expected_event=bootstrap_started`, and `can_stop=true`.
- The expensive pipeline now runs from a daemon worker after the ACK. Status polling should show phase transitions from `queued` into bootstrap/scan/handoff/prediction/risk/execution/export/finalize until a terminal state is written.
- Duplicate starts are rejected with `409` and `code=TEST_CONSOLE_START_REJECTED_ACTIVE_RUN` while preserving the active run metadata.
- Worker exceptions terminalize the run as `FAILED`; operator stops during the worker are preserved as `STOPPED` instead of being overwritten by the worker's final payload.

## Manual validation

1. Open DevTools > Network and filter by `test-console/start`.
2. Press **Run selected profile** with **Scope + Throttle Diagnostics**.
3. Confirm:
   - `OPTIONS /api/mission-control/test-console/start/` returns `200`.
   - `POST /api/mission-control/test-console/start/` returns `202` in less than 2 seconds.
   - The response body contains the run id and `active_run=true` with `display_source=active_run`.
   - Status polling advances from `queued` / `bootstrap` to later phases.

## Expected backend logs

The normal path should show:

- `[test-console] start-view-entered`
- `[test-console] start-request-received`
- `[test-console] start-ack-returned`
- `[test-console] start-worker-dispatched`
- `[test-console] worker-started`
- `[test-console] phase-transition ...`
- `[test-console] worker-completed`

Rejected or failed paths should show:

- `[test-console] start-rejected active-run` for duplicate start attempts.
- `[test-console] worker-failed` if the background pipeline raises.

Use the start ACK as proof that the POST reached the backend. Use subsequent status/export payloads as proof of background execution progress.
