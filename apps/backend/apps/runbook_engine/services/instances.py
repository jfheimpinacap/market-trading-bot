from django.db import transaction

from apps.runbook_engine.models import RunbookInstance, RunbookInstanceStatus, RunbookStep, RunbookStepStatus, RunbookTemplate
from apps.runbook_engine.services.actions import execute_step_action
from apps.runbook_engine.services.progress import ensure_next_step_ready, recalculate_instance_status


@transaction.atomic
def create_runbook_instance(*, template: RunbookTemplate, source_object_type: str, source_object_id: str, priority: str = 'MEDIUM', summary: str = '', metadata: dict | None = None) -> RunbookInstance:
    instance = RunbookInstance.objects.create(
        template=template,
        source_object_type=source_object_type,
        source_object_id=source_object_id,
        status=RunbookInstanceStatus.OPEN,
        priority=priority,
        summary=summary or f'Runbook started from template {template.slug}.',
        metadata=metadata or {},
    )

    step_defs = (template.metadata or {}).get('steps', [])
    for index, step in enumerate(step_defs, start=1):
        RunbookStep.objects.create(
            runbook_instance=instance,
            step_order=index,
            step_type=step.get('step_type', f'step_{index}'),
            title=step.get('title', f'Step {index}'),
            instructions=step.get('instructions', ''),
            action_kind=step.get('action_kind', 'manual'),
            status=RunbookStepStatus.PENDING,
            metadata={'action_name': step.get('action_name', step.get('step_type', f'step_{index}')), **(step.get('metadata') or {})},
        )

    ensure_next_step_ready(instance)
    return instance


@transaction.atomic
def run_step(*, instance: RunbookInstance, step: RunbookStep) -> RunbookStep:
    if step.runbook_instance_id != instance.id:
        raise ValueError('Step does not belong to this runbook instance.')

    if instance.status in [RunbookInstanceStatus.COMPLETED, RunbookInstanceStatus.ABORTED]:
        raise ValueError('Cannot run steps for completed/aborted runbook.')

    if step.status not in [RunbookStepStatus.READY, RunbookStepStatus.PENDING]:
        raise ValueError(f'Step is not runnable in status {step.status}.')

    step.status = RunbookStepStatus.RUNNING
    step.save(update_fields=['status', 'updated_at'])

    action_result = execute_step_action(step=step)
    if action_result.action_status == 'FAILED':
        step.status = RunbookStepStatus.FAILED
    elif action_result.action_status == 'SKIPPED':
        step.status = RunbookStepStatus.SKIPPED
    else:
        step.status = RunbookStepStatus.DONE
    step.save(update_fields=['status', 'updated_at'])

    remaining_pending = instance.steps.filter(status=RunbookStepStatus.PENDING).order_by('step_order', 'id').first()
    if remaining_pending and step.status in [RunbookStepStatus.DONE, RunbookStepStatus.SKIPPED]:
        remaining_pending.status = RunbookStepStatus.READY
        remaining_pending.save(update_fields=['status', 'updated_at'])

    recalculate_instance_status(instance)
    return step


def get_runbook_summary() -> dict:
    queryset = RunbookInstance.objects.all()
    counts = {
        'open': queryset.filter(status=RunbookInstanceStatus.OPEN).count(),
        'in_progress': queryset.filter(status=RunbookInstanceStatus.IN_PROGRESS).count(),
        'blocked': queryset.filter(status=RunbookInstanceStatus.BLOCKED).count(),
        'completed': queryset.filter(status=RunbookInstanceStatus.COMPLETED).count(),
        'escalated': queryset.filter(status=RunbookInstanceStatus.ESCALATED).count(),
        'aborted': queryset.filter(status=RunbookInstanceStatus.ABORTED).count(),
        'total': queryset.count(),
    }
    active = queryset.filter(status__in=[RunbookInstanceStatus.OPEN, RunbookInstanceStatus.IN_PROGRESS, RunbookInstanceStatus.BLOCKED, RunbookInstanceStatus.ESCALATED]).order_by('-updated_at', '-id')[:10]

    top_active = []
    for item in active:
        steps = list(item.steps.order_by('step_order', 'id'))
        done = len([step for step in steps if step.status in ['DONE', 'SKIPPED']])
        total = len(steps)
        next_step = next((step for step in steps if step.status in ['READY', 'PENDING']), None)
        top_active.append({
            'id': item.id,
            'template_slug': item.template.slug,
            'priority': item.priority,
            'status': item.status,
            'source_object_type': item.source_object_type,
            'source_object_id': item.source_object_id,
            'progress': {'done': done, 'total': total},
            'next_step': {'id': next_step.id, 'title': next_step.title, 'status': next_step.status} if next_step else None,
            'updated_at': item.updated_at,
        })

    return {'counts': counts, 'top_active': top_active}
