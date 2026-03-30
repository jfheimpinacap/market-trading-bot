# autonomy_seed_review

Manual-first seed resolution tracker that consumes already-registered `autonomy_seed.GovernanceSeed` artifacts and records their post-registration review outcomes.

## Scope
- Tracks explicit downstream status (`PENDING`, `ACKNOWLEDGED`, `ACCEPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`) without opaque auto-apply.
- Adds auditable run snapshots and recommendation outputs for operator-driven triage.
- Keeps `autonomy_seed` as the source of truth for seed registration and deduplication.

## Out of scope
- No automatic roadmap/scenario/program/manager mutation.
- No real-money or broker/exchange execution.
- No black-box planning or hidden self-learning.
