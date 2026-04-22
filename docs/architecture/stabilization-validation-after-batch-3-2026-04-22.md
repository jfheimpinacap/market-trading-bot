# Stabilization validation after Batch 3 (2026-04-22)

## Scope (strict)

Validation-only pass after Batch 3 to confirm canonical lifecycle/status/export contract consistency across:

- backend serializer + status payload production,
- export JSON/text generation,
- frontend consumption in Dashboard / Cockpit / Test Console surfaces.

No new features, no policy changes, no launcher changes, no LLM/training changes, and no large refactor.

## What improved (confirmed)

1. **Canonical lifecycle contract is now shared across Dashboard and Cockpit consumption.**
   - Both pages use the same lifecycle resolver (`resolveTestConsoleLifecycleState`) for `exists/status(NO_RUN_YET|AVAILABLE)`, active-vs-terminal split, and stop/export capability gates.
2. **Runtime flags are emitted centrally in backend payload shaping.**
   - `is_terminal`, `is_hung`, `has_active_run`, `has_last_completed_run`, `can_stop`, `stop_available`, `can_stop_reason` are now consistently computed in one place before serializer response.
3. **Serializer contract coverage is broad and explicit.**
   - Test Console status serializer includes canonical lifecycle + run identity fields (`current_run_id`, `last_run_id`) plus optional contract fields (`exists/status/reason_code/summary`).
4. **Test Console frontend separation (current run vs last completed run) is structurally preserved.**
   - Cockpit renders current-run panel only when active and keeps terminal snapshot in separate "last completed" block.

## Residual inconsistencies found and addressed here

1. **Cockpit still displayed `IDLE` while Dashboard showed `NO_RUN_YET` for the same contract state.**
   - Root cause: Cockpit primary badge rendered `test_status` directly instead of honoring optional-contract `status=NO_RUN_YET`.
   - Fix applied: Cockpit primary status badge now maps to `NO_RUN_YET` when lifecycle contract says no run exists (same semantic treatment as Dashboard).

2. **Export payload could prefer stale `last_log` over fresher active status when run identity diverged.**
   - Root cause: export path started from `last_log` first, even when in-memory status had moved to a different run (`current_run_id` / `last_run_id`).
   - Fix applied: export now prefers current status snapshot when run identity differs, or when active-running status is newer than `last_log`.

## Validation result

Batch 1+2+3 **did reduce the targeted contradictions materially**. Remaining mismatches are now small and local (presentation and stale-source selection), not structural contract breaks.

## Recommendation for the next batch

✅ **Yes: the next correct batch is polling-by-domain stabilization** (as originally planned), because:

- contract/lifecycle semantics are now largely canonical across backend + frontend,
- major current-vs-last-run confusion is reduced,
- remaining issues are mostly around refresh cadence/source prioritization, which is exactly where domain-polling boundaries should improve determinism and noise control.

## Suggested focus for Batch 4 (polling by domain)

1. Split polling schedules by domain (`lifecycle`, `funnel`, `portfolio`, `runtime_attention`) with explicit freshness windows.
2. Avoid cross-domain payload overwrites when one endpoint lags/fails.
3. Keep run identity (`current_run_id`, `last_run_id`) as an anti-mix guard in polling reducers.
4. Preserve "last good data" per domain to avoid UI backsliding to contradictory transient states.
