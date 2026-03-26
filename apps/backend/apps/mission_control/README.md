# mission_control

Mission control adds a local-first autonomous operations loop over existing components. It does not replace `opportunity_supervisor`; it orchestrates periodic cycles and records auditable session/cycle/step traces.

Scope:
- Paper/demo only.
- No real-money execution.
- Runtime governor + safety guard remain authoritative.
- Explicit start/pause/resume/stop/run-cycle controls.
