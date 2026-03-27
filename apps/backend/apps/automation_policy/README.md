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
