# Prompt 374 – Operational Test Console wide dashboard

Prompt 374 is a frontend-only visual redesign of the Cockpit **Operational Test Console**. It does not change backend services, runner behavior, polling, start/stop/export actions, API contracts, trading policy, or Python services.

## What changed

- Replaced the tall two-column console arrangement with a wide dashboard composition:
  - 4 operational columns on large desktop screens.
  - 2 columns on medium screens.
  - 1 column on mobile.
- Added a compact top summary row for status, effective profile, phase, optional gate/validation/trial status, elapsed time, export readiness, and active/last-completed source.
- Grouped primary operational controls by function:
  - Profile selection and actions.
  - Current state.
  - Stage progress and timer fields.
  - Lifecycle/event state.
- Converted **Current run** and **Last completed** into compact detail strips so they no longer dominate vertical space while keeping diagnostic fields available.
- Added a **Pipeline result** grid for Scan, Handoff, Prediction, Risk, Execution, and Export/finalize modules.
- Moved exported log/raw JSON into a bottom log dock with collapsed/scrollable detail panels so logs do not dominate the operational dashboard.

## Scope guardrails

- Frontend layout/CSS/presentation only.
- No backend or API contract changes.
- No changes to test execution logic, runner lifecycle, polling cadence, start/stop/export/copy handlers, or trading policy.
