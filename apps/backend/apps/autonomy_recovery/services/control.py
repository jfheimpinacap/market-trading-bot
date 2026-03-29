from __future__ import annotations

from django.utils import timezone

from apps.approval_center.models import ApprovalRequest


def _build_approval(*, campaign, kind: str, actor: str) -> ApprovalRequest:
    source_object_id = f'autonomy_recovery:{kind}:{campaign.id}'
    existing = ApprovalRequest.objects.filter(source_type='other', source_object_id=source_object_id, status='PENDING').first()
    if existing:
        return existing
    return ApprovalRequest.objects.create(
        source_type='other',
        source_object_id=source_object_id,
        title=f'Autonomy recovery {kind} approval for campaign #{campaign.id}',
        summary=f'Manual-first autonomy recovery requested {kind} approval for campaign {campaign.title}.',
        priority='HIGH' if kind == 'close' else 'MEDIUM',
        status='PENDING',
        requested_at=timezone.now(),
        metadata={'autonomy_campaign_id': campaign.id, 'autonomy_recovery_kind': kind, 'requested_by': actor},
    )


def request_resume_approval(*, campaign, actor: str):
    return _build_approval(campaign=campaign, kind='resume', actor=actor)


def request_close_approval(*, campaign, actor: str):
    return _build_approval(campaign=campaign, kind='close', actor=actor)
