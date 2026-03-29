from __future__ import annotations

from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_followup.models import CampaignFollowup, FollowupStatus, FollowupType


def has_existing_linked_artifact(*, report: CampaignCloseoutReport, followup_type: str) -> bool:
    if followup_type == FollowupType.MEMORY_INDEX:
        return bool(report.linked_memory_document_id)
    if followup_type == FollowupType.POSTMORTEM_REQUEST:
        return bool(report.linked_postmortem_request)
    if followup_type == FollowupType.ROADMAP_FEEDBACK:
        return bool(report.linked_feedback_artifact)
    return False


def is_duplicate_followup(*, report: CampaignCloseoutReport, followup_type: str) -> bool:
    if has_existing_linked_artifact(report=report, followup_type=followup_type):
        return True
    return CampaignFollowup.objects.filter(
        closeout_report=report,
        followup_type=followup_type,
        followup_status__in=[FollowupStatus.EMITTED, FollowupStatus.DUPLICATE_SKIPPED],
    ).exists()
