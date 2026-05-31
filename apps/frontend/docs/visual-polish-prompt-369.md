# Prompt 369 frontend visual polish

Second frontend-only visual pass after the Prompt 368 compaction work. This pass intentionally avoids backend services, trading policy, runner logic, endpoint contracts, and API behavior.

## Scope

- Reworked the app sidebar into three non-overlapping regions: fixed header/logo, independently scrollable navigation, and fixed footer/meta information.
- Reorganized the large Advanced menu into smaller expandable categories while preserving the existing route paths and link targets.
- Reduced text clipping and overflow risk across compact cards, panels, badges, status strips, tables, key/value rows, and log/raw JSON panels.
- Kept compact density and squared visual tokens from Prompt 368; this is a readability/overflow correction pass rather than a feature pass.

## Advanced categories

Advanced routes are grouped visually as:

- Mission Control / Tests
- Signals & Research
- Prediction & Risk
- Execution / Paper Trading
- Diagnostics / Logs
- System / Settings

The active Advanced category auto-opens so deep pages remain discoverable without expanding one giant menu.

## Overflow/readability notes

- Sidebar navigation owns vertical scroll, so the footer no longer overlays expanded Advanced routes.
- Long labels keep ellipsis in the sidebar only where necessary; full labels remain available via native titles.
- Diagnostic text, reason codes, badges, table cells, status strips, and Test Console logs now prefer controlled wrapping/scrolling instead of edge clipping.
