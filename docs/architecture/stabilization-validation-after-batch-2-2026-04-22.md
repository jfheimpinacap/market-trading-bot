# Stabilization validation after Batch 2 (2026-04-22)

## Scope

Validation-only pass over Batch 1 + Batch 2 surfaces for Mission Control/Test Console/Cockpit/Dashboard.

Out of scope (unchanged): policy, launcher, LLM/training, large refactors.

## What was validated

1. **Current run vs last completed run vs selected profile**
   - Frontend lifecycle resolution path (`resolveTestConsoleLifecycleState`) was reviewed and compared against backend canonical flags.
   - Cockpit run/profile/render logic was checked against lifecycle outputs.
2. **Semantic parity between Cockpit / Dashboard / Test Console payload use**
   - Status mapping paths and terminal/stale handling were reviewed side by side.
3. **Optional status contract (`exists=false`, `NO_RUN_YET`)**
   - Backend optional status payload contract and frontend optional-status request helper were verified.
4. **Polling overlap / refresh behavior**
   - Polling hook overlap protections and Cockpit polling enablement conditions were checked.
5. **Residual redundant shaping**
   - Searched for remaining local heuristics that reinterpret canonical payloads differently per screen.
6. **Export/log linkage to executed run**
   - Export endpoint/service behavior was reviewed for selected-vs-last run coupling.

## Validation result summary

### Symptoms effectively reduced

- **Reduced ambiguity between active and terminal snapshots**: backend now emits canonical lifecycle flags (`is_terminal`, `has_active_run`, `has_last_completed_run`, `can_stop`, `stop_available`) from one place, and frontend lifecycle resolution consumes those flags first. This is a clear reduction versus prior local-only inference. 
- **Cockpit current-vs-historical split is materially cleaner**: Cockpit now derives `currentSnapshot` and `effectiveLastCompletedSnapshot` from a shared resolver, then ties executed profile/scope to that resolved snapshot set.
- **Polling overlap risk reduced**: `usePollingTicker` now has in-flight gating (`inFlight`) per poller and Cockpit only enables high-frequency Test Console polling while run is active or just started.
- **Optional status contract is now coherent** for endpoints that can return no run yet: backend emits `exists=false, status=NO_RUN_YET`, while frontend optional-status helper handles 404 fallback to `null` without exploding.

### Residual inconsistencies / fragility still open

1. **Dashboard still applies local semantic mapping independent of Cockpit tone rules.**
   - Dashboard uses its own `statusTone` buckets and does not consume Cockpit tone helpers.
   - Effect: same raw payload can still render with different tone semantics between screens.

2. **Dashboard lifecycle consumption remains partial.**
   - Dashboard uses lifecycle resolver only for executive phrase; quick-strip badges still map directly from raw status fields.
   - Effect: stale/terminal nuance can still be underrepresented on Dashboard compared with Cockpit.

3. **Export endpoint remains "last log" oriented, not explicit run-id oriented.**
   - `export_test_console_log` resolves from `_get_state_snapshot()` and prefers `last_log`.
   - Effect: if operators expect an explicit selected historical run export, contract is still implicit (latest available), not parameterized.

4. **Residual local heuristics still exist in Cockpit for stop/export UX fallbacks.**
   - Cockpit still keeps safety fallback expressions around `stop_available/can_stop` and export eligibility.
   - Effect: much safer than before, but still not a fully strict E2E typed contract where UI decisions are single-source booleans only.

## Recommendation for Batch 3 focus

**Primary recommendation: tipado end-to-end del contrato canónico (backend serializer -> frontend types -> UI selectors).**

Reasoning:
- Polling centralization by domain would help, but current instability hotspots are now more about **semantic reinterpretation drift** across screens than raw overlap.
- Modularization is desirable, but without stronger typed contract guards, it can preserve hidden divergence.
- A typed canonical status selector layer (shared by Cockpit + Dashboard + Test Console widgets) is the highest-leverage next stabilization step.

Suggested Batch 3 priority order:
1. Canonical typed selectors for lifecycle/tone/terminal/stale/exportability.
2. Then domain-level polling orchestration (after semantic alignment is frozen).
3. Then modularization passes.

## Environment/test notes

- Frontend production build passes for current branch.
- Backend TestConsole suite could not be executed in this environment because PostgreSQL test DB is unavailable on `127.0.0.1:5432`.
