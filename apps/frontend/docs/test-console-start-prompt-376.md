# Prompt 376 – Test Console start POST diagnostics

Scope: Operational Test Console start flow only. This note documents how to validate that `Run selected profile` creates the real `POST /api/mission-control/test-console/start/` request and how to interpret frontend/backend errors.

## DevTools validation: OPTIONS vs POST

1. Open the Cockpit page in a development build and open **DevTools > Network**.
2. Enable **Preserve log** and filter by `test-console/start`.
3. Click **Run selected profile** once.
4. Expected outcomes:
   - **POST appears with 200/202/409**: the click reached the backend. Inspect the JSON response body for `current_run_id`, `active_run`, `status`, `detail`, and `reason_code`.
   - **POST appears with 4xx/5xx**: the request reached the backend but failed. The UI should show `Start failed · HTTP <status> · <body/detail>`.
   - **Only OPTIONS appears**: browser preflight ran but the POST was blocked before dispatch. Check CORS response headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`) and the Console CORS error.
   - **No POST and no OPTIONS appear**: the failure happened before Network dispatch. In development, check Console debug events in order: `start-clicked`, `start-request-building`, `start-request-sending`, then either `start-response-received`, `start-request-aborted`, or `start-request-error`.

## Backend log markers

The start path now has a view-entry marker before serializer validation and before service execution:

- `[test-console] start-view-entered`: Django/DRF entered `StartTestConsoleView.post`; the HTTP POST reached the backend view.
- `[test-console] start-request-received`: the Test Console service accepted the validated request and resolved the selected/effective profile.
- `[test-console] start-accepted`: the service created a run id and active in-memory run state.
- `[test-console] start-rejected`: the view or service rejected the request, for example invalid payload or an already-active run.

If Network shows a POST but the backend log has no `start-view-entered`, verify that the frontend `API_BASE_URL` and Vite proxy point at the backend process whose logs you are reading.

## UI start error meanings

- `Start request did not reach backend or was aborted.`: fetch failed before an HTTP response was available, or the browser aborted the request.
- `Network/CORS error`: the browser reported a network-level or CORS failure; inspect the Console and any OPTIONS preflight in Network.
- `Start request timed out before backend response.`: the UI waited the configured request timeout for the POST response and aborted the request.
- `Start failed · HTTP <status> · <body>`: the backend returned a non-2xx response. The status and backend JSON/detail are shown to make the failure actionable.
- `Start accepted but status not active yet`: the POST returned successfully, but follow-up status polling still does not expose `active_run`, `has_active_run`, `current_run_id`, or `run_id`.
