# autonomy_intake

`autonomy_intake` is the governed **backlog-to-planning handoff** layer.

## Purpose

- Consumes formal `GovernanceBacklogItem` artifacts from `autonomy_backlog`.
- Converts READY/PRIORITIZED items into auditable `PlanningProposal` artifacts.
- Emits intake recommendations and run summaries for manual-first review.
- Classifies proposal targets (`roadmap`, `scenario`, `program`, `manager`, `operator_review`) without mutating downstream modules.

## Non-goals

- No auto-apply to roadmap/scenario/program/manager.
- No broker/exchange execution.
- No black-box planner or opaque ML authority.
- No multi-user orchestration.

## API

- `GET /api/autonomy-intake/candidates/`
- `POST /api/autonomy-intake/run-review/`
- `GET /api/autonomy-intake/proposals/`
- `GET /api/autonomy-intake/recommendations/`
- `GET /api/autonomy-intake/summary/`
- `POST /api/autonomy-intake/emit/<backlog_item_id>/`
- `POST /api/autonomy-intake/acknowledge/<proposal_id>/`
