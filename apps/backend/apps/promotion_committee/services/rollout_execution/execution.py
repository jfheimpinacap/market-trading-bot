from __future__ import annotations

from django.utils import timezone

from apps.promotion_committee.models import (
    ManualRolloutPlan,
    ManualRolloutPlanStatus,
    RolloutExecutionRecord,
    RolloutExecutionRun,
    RolloutExecutionStatus,
)


def register_rollout_execution_records(*, run: RolloutExecutionRun) -> list[RolloutExecutionRecord]:
    plans = list(
        ManualRolloutPlan.objects.select_related('linked_candidate').filter(rollout_status=ManualRolloutPlanStatus.READY).order_by('-created_at', '-id')
    )
    records: list[RolloutExecutionRecord] = []
    for plan in plans:
        record, _ = RolloutExecutionRecord.objects.get_or_create(
            linked_rollout_plan=plan,
            defaults={
                'execution_run': run,
                'execution_status': RolloutExecutionStatus.READY,
                'rationale': 'Rollout plan prepared and ready for explicit manual execution.',
                'reason_codes': ['rollout_plan_ready'],
                'blockers': [],
                'metadata': {'manual_first': True, 'paper_only': True},
            },
        )
        if record.execution_run_id != run.id:
            record.execution_run = run
            record.save(update_fields=['execution_run', 'updated_at'])
        records.append(record)
    return records


def execute_rollout_plan(*, plan: ManualRolloutPlan, actor: str = 'operator', notes: str = '', rationale: str = '') -> RolloutExecutionRecord:
    record, _ = RolloutExecutionRecord.objects.get_or_create(
        linked_rollout_plan=plan,
        defaults={
            'execution_run': RolloutExecutionRun.objects.order_by('-started_at', '-id').first()
            or RolloutExecutionRun.objects.create(started_at=timezone.now(), metadata={'created_for': 'manual_execute_rollout'}),
            'rationale': rationale or 'Manual rollout execution started from ready plan.',
        },
    )

    if record.execution_status == RolloutExecutionStatus.REVERTED:
        record.blockers = list({*record.blockers, 'already_reverted'})
        record.execution_notes = (record.execution_notes + '\nAttempt ignored: rollout already reverted.').strip()
        record.save(update_fields=['blockers', 'execution_notes', 'updated_at'])
        return record

    pre_apply_failed = plan.checkpoint_plans.filter(checkpoint_type='pre_apply_check', checkpoint_status='FAILED').exists()
    if pre_apply_failed:
        record.execution_status = RolloutExecutionStatus.FAILED
        record.blockers = list({*record.blockers, 'pre_apply_check_failed'})
        record.execution_notes = (notes or 'Execution blocked by failed pre-apply checkpoint.').strip()
        record.executed_by = actor
        record.executed_at = timezone.now()
        record.save(update_fields=['execution_status', 'blockers', 'execution_notes', 'executed_by', 'executed_at', 'updated_at'])
        return record

    step_count = len(plan.staged_steps or [])
    record.execution_status = RolloutExecutionStatus.EXECUTED if step_count else RolloutExecutionStatus.EXECUTING
    record.executed_step_count = step_count
    record.executed_by = actor
    record.executed_at = timezone.now()
    record.execution_notes = notes
    if rationale:
        record.rationale = rationale
    record.reason_codes = list({*record.reason_codes, 'manual_execution_recorded'})
    record.save(
        update_fields=[
            'execution_status',
            'executed_step_count',
            'executed_by',
            'executed_at',
            'execution_notes',
            'rationale',
            'reason_codes',
            'updated_at',
        ]
    )

    plan.rollout_status = ManualRolloutPlanStatus.EXECUTED
    plan.executed_by = actor
    plan.executed_at = timezone.now()
    plan.save(update_fields=['rollout_status', 'executed_by', 'executed_at', 'updated_at'])
    return record


def close_rollout_execution(*, execution: RolloutExecutionRecord, actor: str = 'operator', notes: str = '') -> RolloutExecutionRecord:
    if execution.execution_status == RolloutExecutionStatus.ROLLBACK_RECOMMENDED:
        execution.execution_status = RolloutExecutionStatus.PAUSED
    elif execution.execution_status not in {RolloutExecutionStatus.REVERTED, RolloutExecutionStatus.FAILED}:
        execution.execution_status = RolloutExecutionStatus.EXECUTED
    execution.executed_by = execution.executed_by or actor
    execution.execution_notes = (execution.execution_notes + f'\nClosed manually by {actor}. {notes}'.strip()).strip()
    execution.save(update_fields=['execution_status', 'executed_by', 'execution_notes', 'updated_at'])
    return execution
