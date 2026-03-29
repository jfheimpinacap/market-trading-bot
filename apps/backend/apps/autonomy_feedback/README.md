# autonomy_feedback

`autonomy_feedback` is the post-emission governance layer for autonomy follow-ups.

- `autonomy_followup` emits traceable handoffs (`EMITTED` / `DUPLICATE_SKIPPED`).
- `autonomy_feedback` consumes only emitted follow-ups and tracks downstream resolution posture.
- The module keeps manual-first control: runs are explicit, completion is explicit, and roadmap/scenario changes are never auto-applied.

Out of scope:
- real-money execution,
- broker/exchange live trading,
- opaque/automatic learning loops,
- enterprise multi-user orchestration.
