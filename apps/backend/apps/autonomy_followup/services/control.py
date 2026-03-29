from __future__ import annotations

from django.db import transaction

from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_followup.models import CampaignFollowup, FollowupStatus, FollowupType
from apps.autonomy_followup.services.dedup import is_duplicate_followup
from apps.autonomy_followup.services.emission import emit_followup_artifact


def _required_types(report: CampaignCloseoutReport) -> list[str]:
    rows: list[str] = []
    if report.requires_memory_index:
        rows.append(FollowupType.MEMORY_INDEX)
    if report.requires_postmortem:
        rows.append(FollowupType.POSTMORTEM_REQUEST)
    if report.requires_roadmap_feedback:
        rows.append(FollowupType.ROADMAP_FEEDBACK)
    return rows


@transaction.atomic
def emit_followups_for_campaign(*, campaign_id: int, actor: str = 'operator-ui') -> list[CampaignFollowup]:
    report = CampaignCloseoutReport.objects.select_related('campaign').get(campaign_id=campaign_id)
    if report.closeout_status not in {'READY', 'COMPLETED'}:
        raise ValueError('Closeout report must be READY or COMPLETED before follow-up emission.')

    emitted: list[CampaignFollowup] = []
    for followup_type in _required_types(report):
        if is_duplicate_followup(report=report, followup_type=followup_type):
            followup = CampaignFollowup.objects.create(
                campaign=report.campaign,
                closeout_report=report,
                followup_type=followup_type,
                followup_status=FollowupStatus.DUPLICATE_SKIPPED,
                rationale='Duplicate artifact already linked; skipped emission.',
                reason_codes=['duplicate_artifact_detected'],
                blockers=[],
                metadata={'actor': actor},
            )
            emitted.append(followup)
            continue

        followup = CampaignFollowup.objects.create(
            campaign=report.campaign,
            closeout_report=report,
            followup_type=followup_type,
            followup_status=FollowupStatus.READY,
            rationale='Manual-first follow-up emission approved from closeout state.',
            reason_codes=['manual_emit'],
            blockers=[],
            metadata={'actor': actor},
        )
        emitted.append(emit_followup_artifact(report=report, followup=followup, actor=actor))

    if not emitted:
        CampaignFollowup.objects.create(
            campaign=report.campaign,
            closeout_report=report,
            followup_type=FollowupType.ROADMAP_FEEDBACK,
            followup_status=FollowupStatus.PENDING_REVIEW,
            rationale='No follow-up types were marked required by closeout report.',
            reason_codes=['no_followup_required'],
            blockers=['closeout_requires_flags_false'],
            metadata={'actor': actor},
        )

    return emitted
