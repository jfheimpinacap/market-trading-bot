# Prompt 371 – Test Console backend lifecycle observability

This note explains how to read backend lifecycle logs and status payloads for the Mission Control Test Console after Prompt 371.

## Log prefix

All lifecycle messages emitted by the backend use the prefix:

```text
[test-console]
```

Useful events:

- `start-request-received`: the backend received `POST /api/mission-control/test-console/start/` and resolved the selected/effective profile before running any operational step.
- `run-id-assigned`: an in-memory Test Console run id was assigned to the active run.
- `phase-transition`: `current_phase` changed. The log includes `from_phase`, `to_phase`, `run_id`, selected/effective profile, scope, and current status.
- `progress-heartbeat`: `last_progress_at` moved. This is debug-level noise and means the backend observed real progress, not a percent estimate.
- `status-refresh-heartbeat`: a status poll refreshed operational context but did not prove real lifecycle progress. This is debug-level and should not be interpreted as a decision or trade event.
- `status-refresh-real-progress`: a status poll observed a real status marker change.
- `export-generated`: text or JSON export was generated for the current/last run.
- `stop-request-received`: the backend received `POST /api/mission-control/test-console/stop/`.
- `stop-applied`: stop handling completed; any session/runner pause actions and warnings are listed.
- `finalize-slow-warning`: the run stayed in `finalize` longer than expected, but usable terminal/export evidence existed, so the operational outcome was preserved.
- `timeout-real-applied`: the run had no real progress past the configured timeout and no usable finalize export/status, so it was marked `TIMED_OUT`.
- `terminal`: the run entered a terminal status (`STOPPED`, `COMPLETED`, `COMPLETED_WITH_WARNINGS`, `BLOCKED`, `FAILED`, `TIMED_OUT`, or `HUNG`).

## How to diagnose “it looks interrupted”

1. **No `start-request-received` log**
   - The backend did not receive the Test Console start POST in this process/log window.
   - Investigate frontend click handling, browser/network request, auth/proxy routing, or whether a different backend process handled the request.

2. **`start-request-received` exists but no later `phase-transition` or `progress-heartbeat`**
   - The run started but did not advance beyond the last logged `current_phase`/`last_backend_event`.
   - Check `last_progress_at`, `seconds_since_last_progress`, and `next_expected_event` in `GET /api/mission-control/test-console/status/`.

3. **Run is still in progress**
   - Status has `test_status=RUNNING`, `can_stop=true`, `active_run` populated, and `export_available=false` unless a partial text export exists.
   - Backend does not invent percent complete; it reports phase/timestamps and lifecycle events only.

4. **Run was stopped**
   - Logs show `stop-request-received` and `stop-applied`.
   - Status/export have `test_status=STOPPED`, `interrupted_by_stop=true`, `stop_requested_at`, and `terminal_reason` describing the pause action or stop warning.

5. **Finalize was slow but not a real timeout**
   - Logs show `finalize-slow-warning`.
   - Status/export have `TEST_CONSOLE_FINALIZE_SLOW_WARNING`, `export_available=true`, and preserve the operational terminal outcome (`COMPLETED`, `COMPLETED_WITH_WARNINGS`, `BLOCKED`, or `FAILED`).

6. **Real timeout**
   - Logs show `timeout-real-applied`.
   - Status/export have `test_status=TIMED_OUT`, `TEST_CONSOLE_HANG_TIMEOUT`, `hang_detection_reason`, and `lifecycle_warning`/`hang_reason_classification` explaining the phase without progress.

7. **Export available**
   - `export_available=true` means a text/json export can be requested via `GET /api/mission-control/test-console/export-log/?format=text|json`.
   - `export-generated` confirms the backend served the export and records whether it was `text` or `json`.

## Status fields for frontend display

The Test Console status payload now carries normalized lifecycle fields intended for UI display:

- `current_run_id`, `last_run_id`
- `active_run`, `active_run_profile`, `profile`
- `selected_profile`, `effective_profile`
- `display_source`
- `current_phase`
- `elapsed_seconds`
- `last_progress_at`
- `seconds_since_last_progress`
- `last_backend_event`
- `next_expected_event`
- `export_available`
- `can_stop`, `stop_available`, `can_stop_reason`
- `terminal_reason`
- `lifecycle_warning`
- `interrupted_by_stop`
- `interrupted_by_reload`
- `interrupted_by_server_restart`

`interrupted_by_reload` and `interrupted_by_server_restart` remain conservative booleans. The current backend keeps Test Console lifecycle state in memory, so a cold process restart can erase active-run memory; if there is no `start-request-received` in the current backend log window, treat the run as not proven to have started in that process.

## Polling/fetch noise

Cockpit already deduplicates GET requests in the shared frontend API client and has a single owner for Test Console polling (`cockpit:test-console-status`). Prompt 371 did not change frontend polling. If backend logs show many successful summary/status GETs but no Test Console lifecycle POST/log events, interpret that as observability/request evidence rather than a trading or policy failure.
