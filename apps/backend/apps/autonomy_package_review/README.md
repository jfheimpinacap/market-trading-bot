# autonomy_package_review

Manual-first package resolution tracker that sits **after** `autonomy_package` registration.

## Purpose

`autonomy_package` registers auditable governance bundles. `autonomy_package_review` consumes those already-registered bundles and tracks downstream outcomes:

- `PENDING`
- `ACKNOWLEDGED`
- `ADOPTED`
- `DEFERRED`
- `REJECTED`
- `BLOCKED`
- `CLOSED`

This closes the package handoff loop without opaque auto-apply.

## Non-goals

- no real-money execution
- no broker/exchange live execution
- no automatic roadmap/scenario/program/manager mutation
- no black-box planner logic
- no multi-user enterprise orchestration
