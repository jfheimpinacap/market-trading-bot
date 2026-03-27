from apps.runbook_engine.models import RunbookInstance, RunbookInstanceStatus, RunbookStep, RunbookStepStatus


def _next_pending_step(instance: RunbookInstance) -> RunbookStep | None:
    return instance.steps.filter(status__in=[RunbookStepStatus.READY, RunbookStepStatus.PENDING]).order_by('step_order', 'id').first()


def recalculate_instance_status(instance: RunbookInstance) -> RunbookInstance:
    steps = list(instance.steps.order_by('step_order', 'id'))
    if not steps:
        if instance.status != RunbookInstanceStatus.COMPLETED:
            instance.status = RunbookInstanceStatus.COMPLETED
            instance.save(update_fields=['status', 'updated_at'])
        return instance

    if any(step.status == RunbookStepStatus.FAILED for step in steps):
        status = RunbookInstanceStatus.BLOCKED
    elif all(step.status in [RunbookStepStatus.DONE, RunbookStepStatus.SKIPPED] for step in steps):
        status = RunbookInstanceStatus.COMPLETED
    elif any(step.status in [RunbookStepStatus.RUNNING, RunbookStepStatus.DONE] for step in steps):
        status = RunbookInstanceStatus.IN_PROGRESS
    else:
        status = RunbookInstanceStatus.OPEN

    if instance.status != status:
        instance.status = status
        instance.save(update_fields=['status', 'updated_at'])

    return instance


def ensure_next_step_ready(instance: RunbookInstance) -> None:
    next_step = _next_pending_step(instance)
    if next_step and next_step.status == RunbookStepStatus.PENDING:
        next_step.status = RunbookStepStatus.READY
        next_step.save(update_fields=['status', 'updated_at'])
