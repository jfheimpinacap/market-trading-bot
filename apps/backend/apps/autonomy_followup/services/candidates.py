from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_followup.models import FollowupType


@dataclass
class FollowupCandidate:
    campaign_id: int
    campaign_title: str
    closeout_report_id: int
    closeout_status: str
    requires_postmortem: bool
    requires_memory_index: bool
    requires_roadmap_feedback: bool
    existing_memory_document: int | None
    existing_postmortem_request: str | None
    existing_feedback_artifact: str | None
    followup_readiness: str
    blockers: list[str]
    metadata: dict


def build_followup_candidates() -> list[FollowupCandidate]:
    reports = list(CampaignCloseoutReport.objects.select_related('campaign', 'linked_memory_document').order_by('-updated_at', '-id')[:200])
    rows: list[FollowupCandidate] = []

    for report in reports:
        blockers: list[str] = []
        if report.closeout_status not in {'READY', 'COMPLETED'}:
            blockers.append('closeout_not_ready')

        has_any_required = report.requires_postmortem or report.requires_memory_index or report.requires_roadmap_feedback
        if not has_any_required:
            blockers.append('no_required_followups')

        all_already_emitted = True
        if report.requires_memory_index and not report.linked_memory_document_id:
            all_already_emitted = False
        if report.requires_postmortem and not report.linked_postmortem_request:
            all_already_emitted = False
        if report.requires_roadmap_feedback and not report.linked_feedback_artifact:
            all_already_emitted = False

        if blockers:
            readiness = 'BLOCKED'
        elif all_already_emitted:
            readiness = 'ALREADY_EMITTED'
        elif report.closeout_status == 'COMPLETED':
            readiness = 'READY'
        else:
            readiness = 'PARTIAL'

        required_types: list[str] = []
        if report.requires_memory_index:
            required_types.append(FollowupType.MEMORY_INDEX)
        if report.requires_postmortem:
            required_types.append(FollowupType.POSTMORTEM_REQUEST)
        if report.requires_roadmap_feedback:
            required_types.append(FollowupType.ROADMAP_FEEDBACK)

        rows.append(
            FollowupCandidate(
                campaign_id=report.campaign_id,
                campaign_title=report.campaign.title,
                closeout_report_id=report.id,
                closeout_status=report.closeout_status,
                requires_postmortem=report.requires_postmortem,
                requires_memory_index=report.requires_memory_index,
                requires_roadmap_feedback=report.requires_roadmap_feedback,
                existing_memory_document=report.linked_memory_document_id,
                existing_postmortem_request=report.linked_postmortem_request or None,
                existing_feedback_artifact=report.linked_feedback_artifact or None,
                followup_readiness=readiness,
                blockers=blockers,
                metadata={
                    'required_followup_types': required_types,
                    'trace_root_type': 'autonomy_campaign',
                    'trace_root_id': str(report.campaign_id),
                },
            )
        )

    return rows
