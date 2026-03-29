from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.autonomy_launch.models import LaunchAuthorization, LaunchAuthorizationStatus, LaunchAuthorizationType


def upsert_authorization_from_snapshot(*, snapshot, actor: str = 'autonomy-launch-preflight'):
    reason_codes = (snapshot.metadata or {}).get('reason_codes', [])
    requires_approval = snapshot.unresolved_approvals_count > 0 or 'PROGRAM_HIGH_RISK' in reason_codes

    status = LaunchAuthorizationStatus.PENDING_REVIEW
    auth_type = LaunchAuthorizationType.NORMAL_START
    rationale = 'Campaign pending explicit launch review.'
    if snapshot.readiness_status == 'BLOCKED':
        status = LaunchAuthorizationStatus.BLOCKED
        auth_type = LaunchAuthorizationType.BLOCKED_START
        rationale = 'Start blocked by preflight safety checks.'
    elif requires_approval:
        auth_type = LaunchAuthorizationType.APPROVAL_REQUIRED_START
        rationale = 'Start requires approval prior to authorization.'

    approval_request = None
    if requires_approval:
        approval_request, _ = ApprovalRequest.objects.update_or_create(
            source_type=ApprovalSourceType.OTHER,
            source_object_id=f'autonomy_launch:start:{snapshot.campaign_id}',
            defaults={
                'title': f'Launch approval required for campaign #{snapshot.campaign_id}',
                'summary': f'Launch preflight requires explicit approval for {snapshot.campaign.title}.',
                'priority': ApprovalPriority.HIGH,
                'status': ApprovalRequestStatus.PENDING,
                'requested_at': timezone.now(),
                'metadata': {'source': 'autonomy_launch', 'campaign_id': snapshot.campaign_id, 'reason_codes': reason_codes},
            },
        )

    return LaunchAuthorization.objects.create(
        campaign=snapshot.campaign,
        authorization_status=status,
        authorization_type=auth_type,
        rationale=rationale,
        reason_codes=reason_codes,
        requires_approval=requires_approval,
        approved_request=approval_request,
        metadata={'generated_by': actor, 'snapshot_id': snapshot.id},
    )


def authorize_campaign(*, campaign_id: int, actor: str = 'operator-ui') -> LaunchAuthorization:
    latest = LaunchAuthorization.objects.filter(campaign_id=campaign_id).order_by('-created_at', '-id').first()
    if latest and latest.authorization_status == LaunchAuthorizationStatus.BLOCKED:
        return latest
    return LaunchAuthorization.objects.create(
        campaign_id=campaign_id,
        authorization_status=LaunchAuthorizationStatus.AUTHORIZED,
        authorization_type=(latest.authorization_type if latest else LaunchAuthorizationType.NORMAL_START),
        rationale='Manual operator authorization granted.',
        reason_codes=(latest.reason_codes if latest else []),
        requires_approval=bool(latest.requires_approval if latest else False),
        approved_request=(latest.approved_request if latest else None),
        authorized_by=actor,
        authorized_at=timezone.now(),
        expires_at=timezone.now() + timedelta(hours=2),
        metadata={'authorized_from': latest.id if latest else None},
    )


def hold_campaign(*, campaign_id: int, actor: str = 'operator-ui', rationale: str = 'Manual operator hold') -> LaunchAuthorization:
    latest = LaunchAuthorization.objects.filter(campaign_id=campaign_id).order_by('-created_at', '-id').first()
    return LaunchAuthorization.objects.create(
        campaign_id=campaign_id,
        authorization_status=LaunchAuthorizationStatus.HOLD,
        authorization_type=(latest.authorization_type if latest else LaunchAuthorizationType.NORMAL_START),
        rationale=rationale,
        reason_codes=(latest.reason_codes if latest else ['MANUAL_HOLD']),
        requires_approval=bool(latest.requires_approval if latest else False),
        approved_request=(latest.approved_request if latest else None),
        authorized_by=actor,
        metadata={'hold_from': latest.id if latest else None},
    )
