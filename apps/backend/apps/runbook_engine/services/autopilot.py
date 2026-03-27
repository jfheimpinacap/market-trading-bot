from django.db import transaction
from django.utils import timezone

from apps.automation_policy.models import AutomationActionExecutionStatus
from apps.automation_policy.services import execute_decision, resolve_runbook_step
from apps.runbook_engine.models import (
    RunbookApprovalCheckpoint,
    RunbookAutopilotRun,
    RunbookAutopilotRunStatus,
    RunbookAutopilotStepOutcome,
    RunbookAutopilotStepResult,
    RunbookInstance,
    RunbookStep,
    RunbookStepStatus,
)
from apps.runbook_engine.services.approvals import create_approval_checkpoint, resolve_approval_checkpoint
from apps.runbook_engine.services.orchestration import recompute_autopilot_run_counters, summarize_autopilot_run
from apps.runbook_engine.services.progress import ensure_next_step_ready, recalculate_instance_status


def _action_name(step: RunbookStep) -> str:
    return (step.metadata or {}).get('action_name', step.step_type)


def _next_attempt(run: RunbookAutopilotRun, step: RunbookStep) -> int:
    latest = run.step_results.filter(runbook_step=step).order_by('-attempt').first()
    return 1 if not latest else latest.attempt + 1


def _create_step_result(*, run: RunbookAutopilotRun, step: RunbookStep, attempt: int, outcome: str, resolution, action_log=None, error_message: str = '', rationale: str = '') -> RunbookAutopilotStepResult:
    step_result = RunbookAutopilotStepResult.objects.create(
        autopilot_run=run,
        runbook_step=step,
        attempt=attempt,
        outcome=outcome,
        automation_decision_id=resolution.decision_result.decision.id,
        automation_action_log_id=action_log.id if action_log else None,
        runbook_action_result=step.action_results.order_by('-created_at').first(),
        rationale=rationale or resolution.decision_result.decision.rationale,
        error_message=error_message,
        metadata={
            'decision_outcome': resolution.outcome,
            'reason_codes': resolution.decision_result.decision.reason_codes,
            'trace_ref': {
                'root_type': run.runbook_instance.source_object_type,
                'root_id': run.runbook_instance.source_object_id,
            },
        },
    )
    return step_result


def _evaluate_single_step(*, run: RunbookAutopilotRun, step: RunbookStep, attempt: int) -> str:
    resolution = resolve_runbook_step(
        action_type=_action_name(step),
        source_context_type=run.runbook_instance.source_object_type,
        runbook_instance_id=run.runbook_instance_id,
        runbook_step_id=step.id,
        metadata={'autopilot_run_id': run.id, 'attempt': attempt},
    )

    if resolution.blocked:
        _create_step_result(
            run=run,
            step=step,
            attempt=attempt,
            outcome=RunbookAutopilotStepOutcome.BLOCKED,
            resolution=resolution,
            rationale='Blocked by automation guardrail/policy posture.',
        )
        run.status = RunbookAutopilotRunStatus.BLOCKED
        return run.status

    if resolution.approval_required:
        checkpoint = create_approval_checkpoint(
            autopilot_run=run,
            step=step,
            reason='Policy requires explicit approval for this step.',
            constraints=resolution.decision_result.decision.reason_codes,
            context_snapshot=resolution.decision_result.decision.metadata,
        )
        _create_step_result(
            run=run,
            step=step,
            attempt=attempt,
            outcome=RunbookAutopilotStepOutcome.APPROVAL_REQUIRED,
            resolution=resolution,
            rationale='Step paused for approval checkpoint.',
        )
        run.status = RunbookAutopilotRunStatus.PAUSED_FOR_APPROVAL
        run.metadata = {**(run.metadata or {}), 'pending_checkpoint_id': checkpoint.id}
        return run.status

    if resolution.manual_only:
        _create_step_result(
            run=run,
            step=step,
            attempt=attempt,
            outcome=RunbookAutopilotStepOutcome.MANUAL_ONLY,
            resolution=resolution,
            rationale='Manual-only action; autopilot paused for operator execution.',
        )
        run.status = RunbookAutopilotRunStatus.PAUSED_FOR_APPROVAL
        return run.status

    action_log = execute_decision(result=resolution.decision_result, runbook_step=step)
    if action_log.execution_status == AutomationActionExecutionStatus.FAILED:
        step.status = RunbookStepStatus.FAILED
        step.save(update_fields=['status', 'updated_at'])
        _create_step_result(
            run=run,
            step=step,
            attempt=attempt,
            outcome=RunbookAutopilotStepOutcome.FAILED,
            resolution=resolution,
            action_log=action_log,
            error_message=action_log.result_summary,
            rationale='Execution failed while action was auto-executed.',
        )
        run.status = RunbookAutopilotRunStatus.FAILED
        return run.status

    if action_log.execution_status == AutomationActionExecutionStatus.SKIPPED:
        outcome = RunbookAutopilotStepOutcome.SKIPPED
    else:
        outcome = RunbookAutopilotStepOutcome.AUTO_EXECUTED

    _create_step_result(run=run, step=step, attempt=attempt, outcome=outcome, resolution=resolution, action_log=action_log)
    ensure_next_step_ready(run.runbook_instance)
    recalculate_instance_status(run.runbook_instance)
    return run.status


@transaction.atomic
def run_autopilot(*, instance: RunbookInstance, metadata: dict | None = None) -> RunbookAutopilotRun:
    run = RunbookAutopilotRun.objects.create(
        runbook_instance=instance,
        status=RunbookAutopilotRunStatus.RUNNING,
        started_at=timezone.now(),
        metadata=metadata or {},
    )
    return continue_autopilot(autopilot_run=run)


@transaction.atomic
def continue_autopilot(*, autopilot_run: RunbookAutopilotRun, checkpoint: RunbookApprovalCheckpoint | None = None, approved: bool = True, reviewer: str = '') -> RunbookAutopilotRun:
    if checkpoint:
        resolve_approval_checkpoint(checkpoint=checkpoint, approved=approved, reviewer=reviewer)
        if not approved:
            autopilot_run.status = RunbookAutopilotRunStatus.ABORTED
            autopilot_run.finished_at = timezone.now()
            recompute_autopilot_run_counters(autopilot_run=autopilot_run)
            autopilot_run.summary = summarize_autopilot_run(autopilot_run=autopilot_run)
            autopilot_run.save(update_fields=['status', 'finished_at', 'summary', 'updated_at'])
            return autopilot_run

    autopilot_run.status = RunbookAutopilotRunStatus.RUNNING
    autopilot_run.save(update_fields=['status', 'updated_at'])

    while True:
        step = autopilot_run.runbook_instance.steps.filter(status__in=[RunbookStepStatus.READY, RunbookStepStatus.PENDING]).order_by('step_order', 'id').first()
        if not step:
            autopilot_run.status = RunbookAutopilotRunStatus.COMPLETED
            autopilot_run.finished_at = timezone.now()
            recalculate_instance_status(autopilot_run.runbook_instance)
            break

        status_after = _evaluate_single_step(run=autopilot_run, step=step, attempt=_next_attempt(autopilot_run, step))
        if status_after in [RunbookAutopilotRunStatus.PAUSED_FOR_APPROVAL, RunbookAutopilotRunStatus.BLOCKED, RunbookAutopilotRunStatus.FAILED]:
            autopilot_run.finished_at = timezone.now()
            break

    recompute_autopilot_run_counters(autopilot_run=autopilot_run)
    autopilot_run.summary = summarize_autopilot_run(autopilot_run=autopilot_run)
    autopilot_run.save(update_fields=['status', 'finished_at', 'summary', 'metadata', 'updated_at'])
    return autopilot_run


@transaction.atomic
def retry_step(*, autopilot_run: RunbookAutopilotRun, step: RunbookStep, reason: str = '') -> RunbookAutopilotRun:
    step.status = RunbookStepStatus.READY
    step.save(update_fields=['status', 'updated_at'])
    metadata = autopilot_run.metadata or {}
    retries = metadata.get('retries', [])
    retries.append({'step_id': step.id, 'reason': reason, 'requested_at': timezone.now().isoformat()})
    autopilot_run.metadata = {**metadata, 'retries': retries}
    autopilot_run.save(update_fields=['metadata', 'updated_at'])
    return continue_autopilot(autopilot_run=autopilot_run)


def get_autopilot_summary() -> dict:
    runs = RunbookAutopilotRun.objects.all()
    counts = {
        'running': runs.filter(status=RunbookAutopilotRunStatus.RUNNING).count(),
        'paused_for_approval': runs.filter(status=RunbookAutopilotRunStatus.PAUSED_FOR_APPROVAL).count(),
        'blocked': runs.filter(status=RunbookAutopilotRunStatus.BLOCKED).count(),
        'completed': runs.filter(status=RunbookAutopilotRunStatus.COMPLETED).count(),
        'failed': runs.filter(status=RunbookAutopilotRunStatus.FAILED).count(),
        'aborted': runs.filter(status=RunbookAutopilotRunStatus.ABORTED).count(),
        'total': runs.count(),
    }
    recent = runs.order_by('-created_at', '-id')[:10]
    return {
        'counts': counts,
        'recent': [
            {
                'id': run.id,
                'runbook_instance_id': run.runbook_instance_id,
                'status': run.status,
                'summary': run.summary,
                'steps_evaluated': run.steps_evaluated,
                'steps_auto_executed': run.steps_auto_executed,
                'steps_waiting_manual': run.steps_waiting_manual,
                'steps_blocked': run.steps_blocked,
                'updated_at': run.updated_at,
            }
            for run in recent
        ],
    }
