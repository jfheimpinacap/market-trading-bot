from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_closeout.models import CampaignCloseoutReport, CloseoutFinding, CloseoutFindingType
from apps.autonomy_disposition.models import CampaignDisposition
from apps.autonomy_feedback.models import FollowupResolution, ResolutionStatus
from apps.autonomy_followup.models import CampaignFollowup, FollowupType


@dataclass(slots=True)
class InsightCandidate:
    campaign_id: int
    campaign_title: str
    closeout_status: str
    feedback_resolution_status: str
    disposition_type: str
    lifecycle_closed: bool
    major_failure_modes: list[str]
    major_success_factors: list[str]
    approval_friction_level: str
    incident_pressure_level: str
    recovery_complexity_level: str
    roadmap_feedback_present: bool
    memory_followup_resolved: bool
    postmortem_followup_resolved: bool
    metadata: dict


def _level(value: int) -> str:
    if value <= 1:
        return 'LOW'
    if value <= 3:
        return 'MEDIUM'
    return 'HIGH'


def build_insight_candidates() -> list[InsightCandidate]:
    reports = list(CampaignCloseoutReport.objects.select_related('campaign').order_by('-updated_at', '-id'))
    campaign_ids = [report.campaign_id for report in reports]

    followups = CampaignFollowup.objects.filter(campaign_id__in=campaign_ids).select_related('campaign')
    by_campaign_followups: dict[int, list[CampaignFollowup]] = {}
    for followup in followups:
        by_campaign_followups.setdefault(followup.campaign_id, []).append(followup)

    resolutions = FollowupResolution.objects.select_related('followup').filter(campaign_id__in=campaign_ids)
    by_followup_resolution = {resolution.followup_id: resolution for resolution in resolutions}

    latest_dispositions: dict[int, CampaignDisposition] = {}
    for disposition in CampaignDisposition.objects.filter(campaign_id__in=campaign_ids).order_by('campaign_id', '-created_at', '-id'):
        latest_dispositions.setdefault(disposition.campaign_id, disposition)

    finding_rows = CloseoutFinding.objects.filter(closeout_report_id__in=[report.id for report in reports]).values_list(
        'closeout_report_id', 'finding_type', 'summary', 'reason_codes'
    )
    by_report_findings: dict[int, list[tuple[str, str, list[str]]]] = {}
    for report_id, finding_type, summary, reason_codes in finding_rows:
        by_report_findings.setdefault(report_id, []).append((finding_type, summary, reason_codes or []))

    candidates: list[InsightCandidate] = []
    for report in reports:
        campaign_followups = by_campaign_followups.get(report.campaign_id, [])
        emitted_followups = [row for row in campaign_followups if row.followup_status == 'EMITTED']
        emitted_resolutions = [by_followup_resolution.get(row.id) for row in emitted_followups]

        unresolved = [
            resolution
            for resolution in emitted_resolutions
            if resolution is None or resolution.resolution_status not in {ResolutionStatus.COMPLETED, ResolutionStatus.CLOSED, ResolutionStatus.REJECTED}
        ]
        lifecycle_closed = report.closeout_status == 'COMPLETED' and not unresolved

        resolution_status = 'UNRESOLVED'
        if emitted_followups and not unresolved:
            resolution_status = 'COMPLETED'
        elif emitted_followups:
            resolution_status = 'PENDING'

        report_findings = by_report_findings.get(report.id, [])
        major_failure_modes = [summary for finding_type, summary, _ in report_findings if finding_type == CloseoutFindingType.FAILURE_MODE]
        major_success_factors = [summary for finding_type, summary, _ in report_findings if finding_type == CloseoutFindingType.SUCCESS_FACTOR]

        approval_score = len([1 for finding_type, _, _ in report_findings if finding_type == CloseoutFindingType.APPROVAL_FRICTION]) + len(report.major_blockers)
        incident_score = len([1 for finding_type, _, _ in report_findings if finding_type == CloseoutFindingType.INCIDENT_LESSON])
        recovery_score = len([1 for finding_type, _, _ in report_findings if finding_type == CloseoutFindingType.RECOVERY_LESSON])

        memory_followups = [f for f in emitted_followups if f.followup_type == FollowupType.MEMORY_INDEX]
        memory_followup_resolved = bool(memory_followups) and all(
            by_followup_resolution.get(f.id) and by_followup_resolution[f.id].resolution_status in {ResolutionStatus.COMPLETED, ResolutionStatus.CLOSED}
            for f in memory_followups
        )
        postmortem_followups = [f for f in emitted_followups if f.followup_type == FollowupType.POSTMORTEM_REQUEST]
        postmortem_followup_resolved = bool(postmortem_followups) and all(
            by_followup_resolution.get(f.id) and by_followup_resolution[f.id].resolution_status in {ResolutionStatus.COMPLETED, ResolutionStatus.CLOSED}
            for f in postmortem_followups
        )

        latest_disposition = latest_dispositions.get(report.campaign_id)
        disposition_type = latest_disposition.disposition_type if latest_disposition else report.disposition_type

        candidates.append(
            InsightCandidate(
                campaign_id=report.campaign_id,
                campaign_title=report.campaign.title,
                closeout_status=report.closeout_status,
                feedback_resolution_status=resolution_status,
                disposition_type=disposition_type,
                lifecycle_closed=lifecycle_closed,
                major_failure_modes=major_failure_modes,
                major_success_factors=major_success_factors,
                approval_friction_level=_level(approval_score),
                incident_pressure_level=_level(incident_score),
                recovery_complexity_level=_level(recovery_score),
                roadmap_feedback_present=bool(report.requires_roadmap_feedback or report.linked_feedback_artifact),
                memory_followup_resolved=memory_followup_resolved,
                postmortem_followup_resolved=postmortem_followup_resolved,
                metadata={
                    'campaign_status': report.campaign.status,
                    'domains': report.campaign.metadata.get('domains', []) if isinstance(report.campaign.metadata, dict) else [],
                    'followup_count': len(emitted_followups),
                    'unresolved_followups': len(unresolved),
                },
            )
        )

    return candidates
