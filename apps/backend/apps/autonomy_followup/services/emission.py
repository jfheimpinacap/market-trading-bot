from __future__ import annotations

from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_followup.models import CampaignFollowup, FollowupStatus, FollowupType
from apps.memory_retrieval.models import MemoryDocument, MemoryDocumentType


def emit_followup_artifact(*, report: CampaignCloseoutReport, followup: CampaignFollowup, actor: str) -> CampaignFollowup:
    if followup.followup_type == FollowupType.MEMORY_INDEX:
        doc, _ = MemoryDocument.objects.get_or_create(
            source_app='autonomy_followup',
            source_object_id=f'closeout:{report.id}',
            document_type=MemoryDocumentType.LIFECYCLE_DECISION,
            defaults={
                'title': f'Autonomy closeout memory: {report.campaign.title}',
                'text_content': report.final_outcome_summary,
                'structured_summary': {
                    'executive_summary': report.executive_summary,
                    'closeout_status': report.closeout_status,
                    'requires_postmortem': report.requires_postmortem,
                },
                'tags': ['autonomy_closeout', 'autonomy_followup', 'manual_first'],
                'metadata': {'campaign_id': report.campaign_id, 'closeout_report_id': report.id},
            },
        )
        followup.linked_memory_document = doc
        report.linked_memory_document = doc
    elif followup.followup_type == FollowupType.POSTMORTEM_REQUEST:
        source_object_id = f'autonomy_followup:closeout:{report.id}:postmortem'
        request, _ = ApprovalRequest.objects.get_or_create(
            source_type='other',
            source_object_id=source_object_id,
            defaults={
                'title': f'Postmortem request for campaign {report.campaign.title}',
                'summary': report.final_outcome_summary,
                'priority': 'HIGH' if report.requires_postmortem else 'MEDIUM',
                'status': 'PENDING',
                'requested_at': timezone.now(),
                'metadata': {
                    'autonomy_campaign_id': report.campaign_id,
                    'request_kind': 'postmortem_board_request',
                    'trace': {'root_type': 'autonomy_campaign', 'root_id': str(report.campaign_id)},
                },
            },
        )
        followup.linked_postmortem_request = request
        report.linked_postmortem_request = str(request.id)
    elif followup.followup_type == FollowupType.ROADMAP_FEEDBACK:
        artifact_id = report.linked_feedback_artifact or f'roadmap-feedback-closeout-{report.id}'
        followup.linked_feedback_artifact = artifact_id
        report.linked_feedback_artifact = artifact_id
        feedback = report.metadata.get('roadmap_feedback', {})
        report.metadata = {
            **report.metadata,
            'roadmap_feedback': {
                **feedback,
                'artifact_id': artifact_id,
                'campaign_id': report.campaign_id,
                'closeout_report_id': report.id,
                'autonomy_roadmap_link': '/autonomy-roadmap',
                'autonomy_scenario_link': '/autonomy-scenarios',
            },
        }

    followup.followup_status = FollowupStatus.EMITTED
    followup.emitted_by = actor
    followup.emitted_at = timezone.now()
    followup.save(
        update_fields=['followup_status', 'emitted_by', 'emitted_at', 'linked_memory_document', 'linked_postmortem_request', 'linked_feedback_artifact', 'updated_at']
    )
    report.save(update_fields=['linked_memory_document', 'linked_postmortem_request', 'linked_feedback_artifact', 'metadata', 'updated_at'])
    return followup
