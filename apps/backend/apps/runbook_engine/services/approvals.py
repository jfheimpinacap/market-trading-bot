from django.utils import timezone

from apps.runbook_engine.models import RunbookApprovalCheckpoint, RunbookApprovalCheckpointStatus, RunbookAutopilotRun, RunbookStep


def create_approval_checkpoint(*, autopilot_run: RunbookAutopilotRun, step: RunbookStep, reason: str, constraints: list[str] | None = None, context_snapshot: dict | None = None) -> RunbookApprovalCheckpoint:
    return RunbookApprovalCheckpoint.objects.create(
        autopilot_run=autopilot_run,
        runbook_instance=autopilot_run.runbook_instance,
        runbook_step=step,
        approval_reason=reason,
        blocking_constraints=constraints or [],
        context_snapshot=context_snapshot or {},
        status=RunbookApprovalCheckpointStatus.PENDING,
    )


def resolve_approval_checkpoint(*, checkpoint: RunbookApprovalCheckpoint, approved: bool = True, reviewer: str = '') -> RunbookApprovalCheckpoint:
    checkpoint.status = RunbookApprovalCheckpointStatus.APPROVED if approved else RunbookApprovalCheckpointStatus.REJECTED
    checkpoint.approved_at = timezone.now()
    checkpoint.resolved_by = reviewer
    checkpoint.save(update_fields=['status', 'approved_at', 'resolved_by', 'updated_at'])
    return checkpoint
