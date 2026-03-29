# autonomy_activation

Manual-first activation gateway for the final handoff from `autonomy_launch` authorization into `autonomy_campaign.start`.

## Responsibilities
- Consume AUTHORIZED launch records.
- Revalidate posture/window/incidents/domain conflicts at dispatch time.
- Execute explicit dispatch handoff into campaign start.
- Persist auditable activation outcomes (`STARTED`, `BLOCKED`, `FAILED`, `EXPIRED`).
- Emit dispatch recommendations and run snapshots for cockpit/trace visibility.

## Out of scope
- Real-money trading.
- Opaque mass auto-dispatch.
- Distributed scheduler orchestration.
- Multi-user enterprise controls.
