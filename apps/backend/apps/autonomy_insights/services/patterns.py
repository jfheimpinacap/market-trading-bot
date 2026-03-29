from __future__ import annotations

from collections import Counter

from apps.autonomy_insights.models import InsightScope, InsightType, RecommendationTarget

from .synthesis import CampaignSynthesis


def build_pattern_insights(synthesized: list[CampaignSynthesis]) -> list[dict]:
    insights: list[dict] = []

    for row in synthesized:
        campaign = row.candidate
        campaign_status = str(campaign.metadata.get('campaign_status', '')).upper()

        if campaign_status == 'COMPLETED' and row.friction_score <= 4 and campaign.major_success_factors:
            insights.append(
                {
                    'campaign_id': campaign.campaign_id,
                    'insight_type': InsightType.SUCCESS_PATTERN,
                    'scope': InsightScope.CAMPAIGN,
                    'summary': f"Campaign closed with low friction and reusable success factors: {', '.join(campaign.major_success_factors[:2])}.",
                    'evidence_summary': {'success_factors': campaign.major_success_factors, 'friction_score': row.friction_score},
                    'reason_codes': ['low_friction_closeout', 'resolved_followups'],
                    'recommended_followup': 'Prepare curated precedent note for memory retrieval.',
                    'recommendation_target': RecommendationTarget.MEMORY,
                    'confidence': 0.84,
                    'metadata': {'trace_root_type': 'autonomy_campaign', 'trace_root_id': str(campaign.campaign_id)},
                }
            )

        if campaign.disposition_type in {'ABORTED', 'RETIRED'} and campaign.feedback_resolution_status == 'COMPLETED':
            insights.append(
                {
                    'campaign_id': campaign.campaign_id,
                    'insight_type': InsightType.FAILURE_PATTERN,
                    'scope': InsightScope.CAMPAIGN,
                    'summary': 'Campaign ended in abort/retire with resolved follow-ups; governance caution should be codified.',
                    'evidence_summary': {'failure_modes': campaign.major_failure_modes, 'disposition_type': campaign.disposition_type},
                    'reason_codes': ['abort_or_retire', 'followups_resolved'],
                    'recommended_followup': 'Prepare roadmap and scenario caution notes for future planning.',
                    'recommendation_target': RecommendationTarget.ROADMAP,
                    'confidence': 0.79,
                    'metadata': {'trace_root_type': 'autonomy_campaign', 'trace_root_id': str(campaign.campaign_id)},
                }
            )

    blocker_counter: Counter[str] = Counter()
    governance_counter: Counter[str] = Counter()
    for row in synthesized:
        for failure in row.candidate.major_failure_modes:
            blocker_counter[failure.strip().lower()] += 1
        if row.candidate.approval_friction_level == 'HIGH' or row.candidate.roadmap_feedback_present:
            for domain in row.domains or ['global']:
                governance_counter[str(domain)] += 1

    repeated_blockers = [text for text, count in blocker_counter.items() if text and count >= 2]
    if repeated_blockers:
        insights.append(
            {
                'campaign_id': None,
                'insight_type': InsightType.BLOCKER_PATTERN,
                'scope': InsightScope.CROSS_CAMPAIGN,
                'summary': f"Repeated blocker/failure themes detected across campaigns: {', '.join(repeated_blockers[:3])}.",
                'evidence_summary': {'repeated_blockers': repeated_blockers, 'campaign_count': len(synthesized)},
                'reason_codes': ['cross_campaign_repetition'],
                'recommended_followup': 'Prepare program-level blocker mitigation note.',
                'recommendation_target': RecommendationTarget.PROGRAM,
                'confidence': 0.75,
                'metadata': {'domains': sorted(governance_counter.keys())},
            }
        )

    repeated_governance_domains = [domain for domain, count in governance_counter.items() if count >= 2]
    if repeated_governance_domains:
        insights.append(
            {
                'campaign_id': None,
                'insight_type': InsightType.GOVERNANCE_PATTERN,
                'scope': InsightScope.DOMAIN,
                'summary': f"Governance friction repeats in domains: {', '.join(repeated_governance_domains[:4])}.",
                'evidence_summary': {'domains': repeated_governance_domains, 'counts': dict(governance_counter)},
                'reason_codes': ['governance_friction_repetition'],
                'recommended_followup': 'Prepare roadmap/scenario governance feedback package.',
                'recommendation_target': RecommendationTarget.MANAGER,
                'confidence': 0.72,
                'metadata': {'governance_domains': repeated_governance_domains},
            }
        )

    return insights
