from __future__ import annotations

from django.utils import timezone

from apps.autonomy_feedback.models import FollowupResolution, ResolutionStatus
from apps.autonomy_feedback.services.status import evaluate_downstream
from apps.autonomy_followup.models import CampaignFollowup


def mark_resolution_complete(*, followup_id: int, actor: str = 'operator-ui') -> FollowupResolution:
    followup = CampaignFollowup.objects.select_related('campaign', 'linked_memory_document', 'linked_postmortem_request').get(pk=followup_id)
    evaluation = evaluate_downstream(followup)

    if evaluation.resolution_status not in {ResolutionStatus.COMPLETED, ResolutionStatus.REJECTED}:
        raise ValueError('Follow-up does not have enough downstream evidence to complete manually.')

    resolution, created = FollowupResolution.objects.get_or_create(
        followup=followup,
        defaults={
            'campaign': followup.campaign,
            'resolution_status': ResolutionStatus.CLOSED,
            'downstream_status': evaluation.downstream_status,
            'resolution_type': evaluation.resolution_type,
            'rationale': 'Manually closed after downstream completion signals were validated.',
            'reason_codes': evaluation.reason_codes,
            'blockers': [],
            'resolved_by': actor,
            'resolved_at': timezone.now(),
            'linked_memory_document': followup.linked_memory_document,
            'linked_postmortem_request': followup.linked_postmortem_request,
            'linked_feedback_artifact': followup.linked_feedback_artifact,
            'metadata': {'manual_complete': True},
        },
    )
    if created or resolution.resolution_status not in {ResolutionStatus.CLOSED, ResolutionStatus.COMPLETED}:
        resolution.resolution_status = ResolutionStatus.CLOSED
        resolution.downstream_status = evaluation.downstream_status
        resolution.resolution_type = evaluation.resolution_type
        resolution.rationale = 'Manually closed after downstream completion signals were validated.'
        resolution.reason_codes = evaluation.reason_codes
        resolution.blockers = []
        resolution.resolved_by = actor
        resolution.resolved_at = timezone.now()
        resolution.linked_memory_document = followup.linked_memory_document
        resolution.linked_postmortem_request = followup.linked_postmortem_request
        resolution.linked_feedback_artifact = followup.linked_feedback_artifact
        resolution.metadata = {**(resolution.metadata or {}), 'manual_complete': True}
        resolution.save()

    return resolution
