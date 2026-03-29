# autonomy_followup

Manual-first governance layer that consumes `autonomy_closeout` reports and emits auditable follow-up handoffs.

## Scope
- Builds follow-up candidates from closeout report readiness and required handoff flags.
- Emits concrete, traceable handoff artifacts:
  - memory document (`memory_retrieval.MemoryDocument`)
  - postmortem formal request (`approval_center.ApprovalRequest` request stub for postmortem-board routing)
  - roadmap/scenario feedback stub artifact id (persisted on closeout report metadata)
- Records follow-up history (`CampaignFollowup`) with statuses including `EMITTED`, `BLOCKED`, and `DUPLICATE_SKIPPED`.
- Produces recommendation runs (`FollowupRun` + `FollowupRecommendation`) for operator review.

## Out of scope
- No broker/exchange execution.
- No real money flows.
- No opaque auto-learning or auto-apply roadmap changes.
- No multi-user orchestration.
