from apps.automation_policy.models import AutomationActionExecutionStatus, AutomationActionLog
from apps.automation_policy.services.decisions import DecisionResult
from apps.runbook_engine.models import RunbookStep
from apps.runbook_engine.services.actions import execute_step_action


def execute_decision(*, result: DecisionResult, runbook_step: RunbookStep | None = None) -> AutomationActionLog:
    decision = result.decision
    if not result.can_auto_execute:
        return AutomationActionLog.objects.create(
            decision=decision,
            source_runbook_instance_id=decision.runbook_instance_id,
            source_runbook_step_id=decision.runbook_step_id,
            action_name=decision.action_type,
            execution_status=AutomationActionExecutionStatus.SKIPPED,
            result_summary='Action was not auto-executed by policy outcome.',
            metadata={'outcome': decision.outcome},
        )

    if runbook_step is None:
        return AutomationActionLog.objects.create(
            decision=decision,
            source_runbook_instance_id=decision.runbook_instance_id,
            source_runbook_step_id=decision.runbook_step_id,
            action_name=decision.action_type,
            execution_status=AutomationActionExecutionStatus.EXECUTED,
            result_summary='Auto-execution allowed; no direct executor bound for this action.',
            metadata={'outcome': decision.outcome},
        )

    action_result = execute_step_action(step=runbook_step)
    status = AutomationActionExecutionStatus.EXECUTED
    if action_result.action_status == 'FAILED':
        status = AutomationActionExecutionStatus.FAILED
    elif action_result.action_status == 'SKIPPED':
        status = AutomationActionExecutionStatus.SKIPPED

    return AutomationActionLog.objects.create(
        decision=decision,
        source_runbook_instance_id=runbook_step.runbook_instance_id,
        source_runbook_step_id=runbook_step.id,
        action_name=action_result.action_name,
        execution_status=status,
        result_summary=action_result.result_summary,
        output_refs=action_result.output_refs,
        metadata={'runbook_action_status': action_result.action_status},
    )
