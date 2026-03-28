from apps.autonomy_campaign.models import (
    AutonomyCampaignCheckpoint,
    AutonomyCampaignCheckpointStatus,
    AutonomyCampaignCheckpointType,
    AutonomyCampaignStep,
)
from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from django.utils import timezone


def create_checkpoint(*, step: AutonomyCampaignStep, checkpoint_type: str, summary: str, metadata: dict | None = None):
    checkpoint = AutonomyCampaignCheckpoint.objects.create(
        campaign=step.campaign,
        step=step,
        checkpoint_type=checkpoint_type,
        summary=summary,
        metadata=metadata or {},
    )
    return checkpoint


def create_approval_checkpoint(*, step: AutonomyCampaignStep, summary: str, metadata: dict | None = None):
    checkpoint = create_checkpoint(
        step=step,
        checkpoint_type=AutonomyCampaignCheckpointType.APPROVAL_REQUIRED,
        summary=summary,
        metadata=metadata,
    )
    approval = ApprovalRequest.objects.create(
        source_type=ApprovalSourceType.OTHER,
        source_object_id=f'autonomy_campaign_checkpoint:{checkpoint.id}',
        title=f'Autonomy campaign approval: {step.campaign.title}',
        summary=summary,
        priority=ApprovalPriority.HIGH,
        status=ApprovalRequestStatus.PENDING,
        requested_at=timezone.now(),
        metadata={
            **(metadata or {}),
            'autonomy_campaign_id': step.campaign_id,
            'autonomy_campaign_step_id': step.id,
            'autonomy_campaign_checkpoint_id': checkpoint.id,
            'trace': {'root_type': 'autonomy_campaign', 'root_id': str(step.campaign_id)},
        },
    )
    checkpoint.metadata = {**(checkpoint.metadata or {}), 'approval_request_id': approval.id}
    checkpoint.save(update_fields=['metadata', 'updated_at'])
    return checkpoint


def sync_open_checkpoints(campaign_id: int) -> None:
    open_items = AutonomyCampaignCheckpoint.objects.filter(campaign_id=campaign_id, status=AutonomyCampaignCheckpointStatus.OPEN)
    for checkpoint in open_items:
        approval_id = (checkpoint.metadata or {}).get('approval_request_id')
        if not approval_id:
            continue
        approval = ApprovalRequest.objects.filter(pk=approval_id).first()
        if not approval:
            continue
        if approval.status == ApprovalRequestStatus.APPROVED:
            checkpoint.status = AutonomyCampaignCheckpointStatus.SATISFIED
        elif approval.status == ApprovalRequestStatus.REJECTED:
            checkpoint.status = AutonomyCampaignCheckpointStatus.REJECTED
        elif approval.status == ApprovalRequestStatus.EXPIRED:
            checkpoint.status = AutonomyCampaignCheckpointStatus.EXPIRED
        else:
            continue
        checkpoint.save(update_fields=['status', 'updated_at'])
