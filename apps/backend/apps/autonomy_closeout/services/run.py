from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_closeout.models import (
    CampaignCloseoutReport,
    CampaignCloseoutStatus,
    CloseoutFinding,
    CloseoutRecommendation,
    CloseoutRecommendationType,
    CloseoutRun,
)
from apps.autonomy_closeout.services.candidates import build_closeout_candidates
from apps.autonomy_closeout.services.findings import derive_closeout_findings
from apps.autonomy_closeout.services.handoff import build_handoff_plan
from apps.autonomy_closeout.services.summary import build_closeout_summary


def _status_for_candidate(candidate) -> str:
    if candidate.unresolved_blockers:
        return CampaignCloseoutStatus.BLOCKED
    if candidate.disposition.disposition_status == 'APPROVAL_REQUIRED':
        return CampaignCloseoutStatus.APPROVAL_REQUIRED
    if candidate.ready_for_closeout:
        return CampaignCloseoutStatus.READY
    return CampaignCloseoutStatus.PENDING_REVIEW


@transaction.atomic
def run_closeout_review(*, actor: str = 'operator-ui'):
    candidates = build_closeout_candidates()

    reports: list[CampaignCloseoutReport] = []
    recommendations: list[CloseoutRecommendation] = []

    run = CloseoutRun.objects.create(metadata={'actor': actor})

    for candidate in candidates:
        summary = build_closeout_summary(candidate)
        handoff = build_handoff_plan(candidate, summary)
        report, _ = CampaignCloseoutReport.objects.update_or_create(
            campaign=candidate.campaign,
            defaults={
                'disposition_type': candidate.disposition.disposition_type,
                'closeout_status': _status_for_candidate(candidate),
                'executive_summary': summary['executive_summary'],
                'lifecycle_summary': summary['lifecycle_summary'],
                'major_blockers': summary['major_blockers'],
                'incident_summary': summary['incident_summary'],
                'intervention_summary': summary['intervention_summary'],
                'recovery_summary': summary['recovery_summary'],
                'final_outcome_summary': summary['final_outcome_summary'],
                'requires_postmortem': candidate.requires_postmortem,
                'requires_memory_index': candidate.requires_memory_index,
                'requires_roadmap_feedback': candidate.requires_roadmap_feedback,
                'metadata': {
                    'actor': actor,
                    'campaign_status': candidate.campaign.status,
                    'disposition_status': candidate.disposition.disposition_status,
                    'unresolved_approvals_count': candidate.unresolved_approvals_count,
                    'incident_history_level': candidate.incident_history_level,
                    'intervention_count': candidate.intervention_count,
                    **handoff,
                },
            },
        )
        reports.append(report)

        report.findings.all().delete()
        for finding_payload in derive_closeout_findings(candidate, summary):
            CloseoutFinding.objects.create(closeout_report=report, **finding_payload)

        if candidate.ready_for_closeout:
            recommendations.append(
                CloseoutRecommendation.objects.create(
                    closeout_run=run,
                    recommendation_type=CloseoutRecommendationType.COMPLETE_CLOSEOUT,
                    target_campaign=candidate.campaign,
                    rationale='Campaign has applied disposition and no unresolved closeout blockers.',
                    reason_codes=['ready_for_closeout'],
                    confidence=0.9,
                    blockers=[],
                    impacted_domains=candidate.campaign.metadata.get('domains', []),
                    metadata={'actor': actor},
                )
            )
        else:
            rec_type = (
                CloseoutRecommendationType.REQUIRE_MANUAL_CLOSEOUT_REVIEW
                if candidate.unresolved_blockers or candidate.unresolved_approvals_count
                else CloseoutRecommendationType.KEEP_OPEN_FOR_FOLLOWUP
            )
            recommendations.append(
                CloseoutRecommendation.objects.create(
                    closeout_run=run,
                    recommendation_type=rec_type,
                    target_campaign=candidate.campaign,
                    rationale='Campaign still has unresolved closure ambiguity or blockers.',
                    reason_codes=['manual_review_required'],
                    confidence=0.8,
                    blockers=candidate.unresolved_blockers,
                    impacted_domains=candidate.campaign.metadata.get('domains', []),
                    metadata={'actor': actor},
                )
            )

        if candidate.requires_postmortem:
            recommendations.append(
                CloseoutRecommendation.objects.create(
                    closeout_run=run,
                    recommendation_type=CloseoutRecommendationType.SEND_TO_POSTMORTEM,
                    target_campaign=candidate.campaign,
                    rationale='Disposition and incident history indicate formal postmortem should be queued.',
                    reason_codes=['abort_or_retire_with_incidents'],
                    confidence=0.85,
                    blockers=candidate.unresolved_blockers,
                    impacted_domains=candidate.campaign.metadata.get('domains', []),
                    metadata={'actor': actor},
                )
            )
        if candidate.requires_memory_index:
            recommendations.append(
                CloseoutRecommendation.objects.create(
                    closeout_run=run,
                    recommendation_type=CloseoutRecommendationType.INDEX_IN_MEMORY,
                    target_campaign=candidate.campaign,
                    rationale='Disposition completed cleanly and should be indexed as reusable precedent.',
                    reason_codes=['closeout_memory_candidate'],
                    confidence=0.9,
                    blockers=[],
                    impacted_domains=candidate.campaign.metadata.get('domains', []),
                    metadata={'actor': actor},
                )
            )
        if candidate.requires_roadmap_feedback:
            recommendations.append(
                CloseoutRecommendation.objects.create(
                    closeout_run=run,
                    recommendation_type=CloseoutRecommendationType.PREPARE_ROADMAP_FEEDBACK,
                    target_campaign=candidate.campaign,
                    rationale='Dependency friction or intervention churn suggests roadmap/scenario feedback.',
                    reason_codes=['roadmap_feedback_candidate'],
                    confidence=0.75,
                    blockers=[],
                    impacted_domains=candidate.campaign.metadata.get('domains', []),
                    metadata={'actor': actor},
                )
            )

    ready_campaigns = [item for item in candidates if item.ready_for_closeout]
    if len(ready_campaigns) > 1:
        recommendations.append(
            CloseoutRecommendation.objects.create(
                closeout_run=run,
                recommendation_type=CloseoutRecommendationType.REORDER_CLOSEOUT_PRIORITY,
                rationale='Multiple campaigns are ready for closeout; prioritize high-risk histories first.',
                reason_codes=['multiple_ready_closeouts'],
                confidence=0.7,
                blockers=[],
                impacted_domains=[],
                metadata={'actor': actor, 'priority_campaign_ids': [item.campaign.id for item in ready_campaigns]},
            )
        )

    run.candidate_count = len(candidates)
    run.ready_count = sum(1 for item in candidates if item.ready_for_closeout)
    run.blocked_count = sum(1 for item in candidates if item.unresolved_blockers)
    run.requires_postmortem_count = sum(1 for item in candidates if item.requires_postmortem)
    run.requires_memory_index_count = sum(1 for item in candidates if item.requires_memory_index)
    run.requires_roadmap_feedback_count = sum(1 for item in candidates if item.requires_roadmap_feedback)
    run.completed_closeout_count = CampaignCloseoutReport.objects.filter(closeout_status=CampaignCloseoutStatus.COMPLETED).count()
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(
        update_fields=[
            'candidate_count',
            'ready_count',
            'blocked_count',
            'requires_postmortem_count',
            'requires_memory_index_count',
            'requires_roadmap_feedback_count',
            'completed_closeout_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {'run': run, 'reports': reports, 'recommendations': recommendations}
