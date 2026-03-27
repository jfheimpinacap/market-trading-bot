# automation_policy

Trust-tiered automation policy matrix for supervised runbook autopilot in paper/sandbox mode.

## Scope
- Evaluates operational actions under explicit trust tiers.
- Produces auditable `AutomationDecision` records.
- Logs every attempted/auto-executed action in `AutomationActionLog`.
- Integrates guardrail posture from runtime, safety, certification, and degraded mode.

## Non-goals
- No live money.
- No real execution.
- No opaque planner/autonomous black-box remediation.
- No multi-user enterprise workflow.

## Runbook step resolution integration (new)

`automation_policy.services.runbook_resolution` provides a narrow adapter for runbook autopilot:

- wraps `evaluate_action` for runbook step context
- returns explicit flags (`should_auto_execute`, `approval_required`, `manual_only`, `blocked`)
- preserves guardrail effects from runtime/safety/certification/degraded posture

This preserves automation policy as the single source of truth for trust-tier decisions while enabling per-step supervised runbook orchestration.
