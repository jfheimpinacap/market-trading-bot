# Prompt 381 — Test Console lifecycle tracing repair

Prompt 380 left the Operational Test Console tracing incomplete: the backend could still report an internal raw phase such as `trial` in a timeout reason while the UI displayed the same work as `execution`, and the persistent/auditable trail was not reliable enough to diagnose a run after the launcher/backend console was gone.

This repair keeps the scope limited to Test Console lifecycle observability. It does not change trading policy, risk decisions, LLM/training paths, or real execution behavior; the run remains in paper / `live_read_only_paper_conservative` mode.

## What was repaired

- Persistent JSONL logging now writes to `logs/test_console.log` and creates `logs/` if needed.
- Log write failures are defensive: they are swallowed after a debug log so they cannot break the run.
- Events include enough correlation fields to filter by `run_id`: timestamp, profile, visible phase, raw phase, subphase, event, next expected event, elapsed seconds and reason code when present.
- Each run carries an in-memory lifecycle timeline and a compact `lifecycle_timeline_summary` with the latest 10 events and slowest observed subphase.
- Timeout reasons now include visible phase, raw phase and subphase, for example `HANG_DETECTED_NO_PROGRESS_2072s_PHASE_execution_RAW_trial_SUBPHASE_execution_route_diagnostics_started`.
- `timeout_source` explains the timeout inputs: visible phase, raw phase, subphase, seconds without progress, budget, last backend event, last real progress, worker liveness and export state.
- Worker-active heartbeats are marked as heartbeat activity instead of functional progress, while still updating `last_progress_at` to avoid false no-progress terminalization when the worker is alive.
- Export text/json now includes `lifecycle_timeline_summary`, `persistent_log_path`, `timeout_source`, last subphase, raw phase and a compact interpretation block.

## How to read `logs/test_console.log`

The file is JSONL: each line is one event. To inspect one run:

```bash
python - <<'PY'
import json
run_id = 'tc-REPLACE-ME'
with open('logs/test_console.log', encoding='utf-8') as handle:
    for line in handle:
        event = json.loads(line)
        if event.get('run_id') == run_id:
            print(event['timestamp'], event['event'], event.get('phase'), event.get('raw_phase'), event.get('current_subphase'))
PY
```

Expected minimum sequence for Scope + Throttle Diagnostics is:

1. `start-ack-returned`
2. `worker-started`
3. `phase-transition`
4. `subphase-transition`
5. `progress-heartbeat` or `WORKER_ACTIVE_HEARTBEAT`
6. `export-generated` or `timeout-detected`

## Phase/raw phase/subphase interpretation

- `phase` is the visible phase intended for operators/UI.
- `raw_phase` preserves the backend internal phase. For example, raw `trial` maps to visible `execution`.
- `current_subphase` / `subphase` identifies the diagnostic substep, such as `risk_throttle_diagnostics_started` or `execution_route_diagnostics_completed`.

## Timeout interpretation

- A real timeout has no functional progress and no valid worker heartbeat inside the budget.
- A possible missing-heartbeat timeout is indicated when the timeout lacks worker liveness evidence or has incomplete heartbeat data.
- If a final usable export already exists, the export state in `timeout_source` indicates whether the export is `partial`, `final`, or absent so operators can decide whether the timeout is only a lifecycle warning or the dominant operational outcome.
