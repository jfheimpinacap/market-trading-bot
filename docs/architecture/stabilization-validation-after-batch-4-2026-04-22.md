# Stabilization validation after Batch 4 (2026-04-22)

Validation-only pass focused on post-Batch-4 polling-by-domain behavior across Dashboard, Cockpit, and Test Console surfaces.

## Scope verified

- Polling drift by domain cadence (`lifecycle`, `funnel`, `portfolio`, `runtime attention`).
- Hidden/inactive-state polling suppression.
- Idle/no-run backoff behavior.
- Residual overlap risk across ticks.
- Stale payload backsliding protections (`current_run_id` / `last_run_id` + timestamp freshness).

## What improved (confirmed)

1. **Polling overlap control is materially stronger and shared.**
   - `usePollingTicker` enforces per-poller `inFlight` gating and timeout scheduling (not fixed interval), reducing self-overlap during slow requests.
2. **Visibility/focus behavior is now consistently guarded.**
   - Pollers pause when tab is hidden and resume via focus/visibility trigger, lowering unnecessary hidden-view refresh.
3. **Idle/no-run behavior now backs off instead of staying hot.**
   - Dashboard and Cockpit status pollers now return `idle` signals and allow exponential backoff windows when no active run is present.
4. **Run-identity freshness guard is active in Cockpit Test Console status.**
   - Incoming payloads are rejected when run identity changes with older `updated_at` or when timestamp regresses, preventing stale overwrite/backsliding.
5. **Domain cadence separation exists and is explicit in Cockpit.**
   - Lifecycle/test-console cadence is tighter than deferred funnel/portfolio/runtime domains, reducing forced coupling.

## Residual inconsistencies found

1. **Funnel poller idle detection used local state instead of the just-fetched trial payload.**
   - Risk: one-tick lag in idle detection could keep funnel cadence hotter than needed after trial transitions.
   - Safe fix applied: idle decision now derives from the same fetch response returned by `loadLivePaperTrialStatus`.
2. **Runtime attention cadence still shares a combined callback for summaries + advanced.**
   - Not incorrect, but still a light coupling between two data slices under one domain ticker.
   - This is acceptable for stabilization phase; candidate for modularization phase.

## Recommendation

✅ **Next step: (a) modularización grande**.

Reasoning:
- Batch 4 goals are validated as materially effective on the target symptoms (drift, hidden refresh noise, idle pressure, stale backsliding).
- Remaining issues are now mostly structural/maintainability coupling, not high-risk stabilization regressions.
- Additional small stabilization batch is optional but not required to safely move into modularization.

