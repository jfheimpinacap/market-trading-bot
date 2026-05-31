# Prompt 370 – Cockpit/Test Console visual validation pass

Prompt 370 is a frontend-only follow-up to the Prompt 368 compaction and Prompt 369 overflow/sidebar pass. It targets the Cockpit `Operational Test Console` after real visual validation showed remaining clipped controls and short labels splitting inside the Mission Control/Test Console area.

## Scope

- Redesign the Test Console internals into distinct profile, state, actions, progress/timer, current run, last completed, and export/log areas.
- Keep API contracts, polling, start/stop/export behavior, backend services, runner code, and trading policy untouched.
- Preserve scrollable raw logs/JSON while making long reason codes wrap only inside values/log-oriented blocks.

## Visual fixes

- Desktop Test Console uses a two-column internal layout: left for profile/state/current/last, right for actions/progress/timer.
- Narrow screens fall back to one column.
- Action buttons wrap as an internal grid and stay inside the card.
- Profile selection has a full-width selector row instead of sharing a compressed button row.
- The phase rail is always visible for the active or last displayed run and is labeled as stage-based progress, not a real backend percentage.
- Key/value rows now reserve readable label width so labels such as `Status`, `Summary`, and `Operator hint` do not break letter-by-letter.
- Sidebar navigation keeps its own scroll and the compact footer remains outside the navigation scroll area so expanded Advanced groups are not hidden behind it.
