# autonomy_advisory

Manual-first advisory emission layer that consumes reviewed autonomy insights and issues auditable advisory artifacts.

## Scope
- Consumes `CampaignInsight` and routes reviewed items into formal advisory artifacts.
- Keeps recommendation-first flow with explicit statuses (`EMITTED`, `BLOCKED`, `DUPLICATE_SKIPPED`, etc.).
- Avoids auto-apply to roadmap/scenario/program/manager and only emits traceable notes/stubs.
- Supports local-first single-user operation in paper/sandbox mode.

## Out of scope
- Real broker/exchange execution.
- Opaque auto-learning or black-box planners.
- Multi-user orchestration.
