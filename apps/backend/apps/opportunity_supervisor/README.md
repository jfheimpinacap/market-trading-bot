# opportunity_supervisor

End-to-end supervisor layer for **paper/demo-only** opportunity cycles:

1. run signal fusion (research + prediction + risk context)
2. create proposal candidates
3. run allocation pre-check
4. resolve final execution path (`WATCH`, `PROPOSAL_ONLY`, `QUEUE`, `AUTO_EXECUTE_PAPER`, `BLOCKED`)
5. persist cycle run + per-opportunity item + explicit execution plan snapshot.

This module does **not** enable real-money execution.
