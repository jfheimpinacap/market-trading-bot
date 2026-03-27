from dataclasses import dataclass

from apps.automation_policy.models import AutomationDecisionOutcome
from apps.automation_policy.services.decisions import DecisionResult, evaluate_action


@dataclass
class RunbookStepResolution:
    decision_result: DecisionResult
    outcome: str
    should_auto_execute: bool
    approval_required: bool
    manual_only: bool
    blocked: bool


def resolve_runbook_step(*, action_type: str, source_context_type: str, runbook_instance_id: int, runbook_step_id: int, metadata: dict | None = None) -> RunbookStepResolution:
    decision_result = evaluate_action(
        action_type=action_type,
        source_context_type=source_context_type,
        runbook_instance_id=runbook_instance_id,
        runbook_step_id=runbook_step_id,
        metadata=metadata or {},
    )

    outcome = decision_result.decision.outcome
    return RunbookStepResolution(
        decision_result=decision_result,
        outcome=outcome,
        should_auto_execute=decision_result.can_auto_execute,
        approval_required=outcome == AutomationDecisionOutcome.APPROVAL_REQUIRED,
        manual_only=outcome == AutomationDecisionOutcome.MANUAL_ONLY,
        blocked=outcome == AutomationDecisionOutcome.BLOCKED,
    )
