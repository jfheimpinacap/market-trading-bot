# approval_center

Approval Center is the unified manual-first control plane for explicit human decisions across runbook checkpoints, go-live requests, and approval-required operator queue items.

## Scope
- Centralize pending approvals from multiple modules without replacing source models.
- Expose unified request lifecycle (PENDING, APPROVED, REJECTED, EXPIRED, ESCALATED, CANCELLED).
- Record explicit human decision events with rationale (`ApprovalDecision`).
- Provide impact preview text before acting.

## In scope
- Paper/sandbox only.
- Single-user local operator flow.
- Reuse existing runbook/go-live/operator queue services for real side effects.

## Out of scope (for now)
- Live-money enablement.
- Real execution activation.
- Multi-user approval chains/signatures.
- Opaque planner-based automation.
