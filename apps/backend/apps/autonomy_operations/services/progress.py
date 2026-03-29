from __future__ import annotations

from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaignStepStatus
from apps.autonomy_operations.models import CampaignRuntimeStatus
from apps.autonomy_operations.services.runtime import RuntimeContext

STALL_THRESHOLD_SECONDS = 45 * 60
APPROVAL_DELAY_SECONDS = 30 * 60


def _step_progress_timestamp(context: RuntimeContext):
    steps = list(context.campaign.steps.all())
    done = [step.updated_at for step in steps if step.status in {AutonomyCampaignStepStatus.DONE, AutonomyCampaignStepStatus.RUNNING}]
    if done:
        return max(done)
    return context.campaign.updated_at


def compute_progress(context: RuntimeContext) -> dict:
    now = timezone.now()
    last_progress_at = _step_progress_timestamp(context)
    stalled_duration_seconds = int(max(0, (now - last_progress_at).total_seconds())) if last_progress_at else None

    progress_score = 0.0
    if context.campaign.total_steps > 0:
        progress_score = round((context.campaign.completed_steps / context.campaign.total_steps) * 100, 2)

    runtime_status = CampaignRuntimeStatus.ON_TRACK
    if context.pending_approvals_count > 0:
        runtime_status = CampaignRuntimeStatus.WAITING_APPROVAL
    elif context.campaign.status == 'BLOCKED' or context.blocked_steps_count > 0:
        runtime_status = CampaignRuntimeStatus.BLOCKED
    elif context.current_step and context.current_step.status == AutonomyCampaignStepStatus.OBSERVING:
        runtime_status = CampaignRuntimeStatus.OBSERVING
    elif stalled_duration_seconds and stalled_duration_seconds >= STALL_THRESHOLD_SECONDS:
        runtime_status = CampaignRuntimeStatus.STALLED
    elif context.rollout_observation_impact > 0 or context.incident_impact > 0 or context.degraded_impact > 0:
        runtime_status = CampaignRuntimeStatus.CAUTION

    if runtime_status == CampaignRuntimeStatus.WAITING_APPROVAL and stalled_duration_seconds and stalled_duration_seconds >= APPROVAL_DELAY_SECONDS:
        # keep WAITING_APPROVAL, but recommendation/signal will escalate severity
        pass

    return {
        'last_progress_at': last_progress_at,
        'stalled_duration_seconds': stalled_duration_seconds,
        'progress_score': progress_score,
        'runtime_status': runtime_status,
    }
