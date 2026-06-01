# Prompt 377 – Test Console start request priority

Scope: Operational Test Console frontend start flow only. No trading policy, risk, execution, LLM, or training logic changed.

## Cause detected

After Prompt 376 the Cockpit UI was building the correct `POST /api/mission-control/test-console/start/`, but DevTools showed the `start/` fetch as **cancelled** with `0 KB` after roughly one minute while several secondary GETs (`status/`, `live-paper-validation/`, paper summaries, and dashboard summaries) stayed pending.

That pattern means the click reached frontend code, but the POST could be starved or aborted in the browser/client before Django received it. In that case backend logs will not include either of these markers:

- `[test-console] start-view-entered`
- `[test-console] start-request-received`

## POST failed in backend vs POST cancelled in client

- **Backend failure:** DevTools shows the POST with an HTTP status (for example 400/409/500). The backend should log `[test-console] start-view-entered`; the UI reports `Start failed · HTTP <status> · ...`.
- **Client/browser cancellation:** DevTools shows `start/` as cancelled, often `0 KB`, or no POST reaches the backend. Backend logs do not show `start-view-entered`. The UI reports one of the client-side diagnostics:
  - `Start request aborted by client`
  - `Start request starved by pending requests`
  - `POST did not reach backend; polling was paused for retry`

## Frontend mitigation

`POST /api/mission-control/test-console/start/` now uses the shared API client's critical mutation path:

1. Creates a start-specific request path, not a GET cache/dedupe entry.
2. Pauses Cockpit secondary polling before dispatching start.
3. Aborts non-critical in-flight GETs where the client owns the request controller, while allowing `test-console/status/` to continue.
4. Dispatches start without waiting for secondary pollers.
5. Clears GET success cache only after the critical mutation completes.
6. Restores normal polling after success, failure, not-confirmed, or timeout.

Dev-only Console markers to inspect:

- `start-post-created`
- `start-post-dispatched`
- `start-post-aborted`
- `start-post-timeout`
- `start-post-starved`
- `polling-paused-for-start`
- `polling-resumed-after-start`

## DevTools validation

1. Open the Cockpit page in a development build.
2. Open **DevTools > Network** and enable **Preserve log**.
3. Filter by `test-console/start`.
4. Click **Run selected profile** once.
5. Confirm:
   - `POST /api/mission-control/test-console/start/` appears immediately.
   - The POST is not cancelled and has a response status/body.
   - Backend logs show `[test-console] start-view-entered`.
   - The UI advances to `active_run=true` with `run_id`/`current_run_id` when accepted.
6. While the UI says `Start requested`, verify Network is not flooded with secondary GETs such as `live-paper-validation/`, paper summaries, scan-agent summaries, or runtime dashboard summaries. `test-console/status/` may continue.
