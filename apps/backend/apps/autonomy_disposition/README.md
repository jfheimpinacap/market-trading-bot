# autonomy_disposition

Manual-first campaign closure committee and retirement governance layer.

## Scope
- Consolidates disposition candidates after operations/recovery/interventions.
- Produces auditable disposition decisions (`CLOSED`, `ABORTED`, `RETIRED`, `COMPLETED_RECORDED`, `KEPT_OPEN`).
- Supports approval gating for sensitive dispositions before apply.
- Applies final disposition with explicit before/after campaign state recording.

## Out of scope
- Real-money trading or live broker/exchange execution.
- Opaque auto-close, auto-abort, or auto-retire.
- Planner black-box logic, ML authority, or distributed enterprise orchestration.
