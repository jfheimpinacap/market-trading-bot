from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_insights.models import CampaignInsight, InsightRecommendation, InsightRun, InsightType

from .candidates import build_insight_candidates
from .patterns import build_pattern_insights
from .recommendation import build_insight_recommendations
from .synthesis import synthesize_campaign_evidence


@transaction.atomic
def run_insight_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_insight_candidates()
    synthesized = synthesize_campaign_evidence(candidates)

    run = InsightRun.objects.create(metadata={'actor': actor})

    created_insights: list[CampaignInsight] = []
    for row in build_pattern_insights(synthesized):
        created_insights.append(
            CampaignInsight.objects.create(
                campaign_id=row['campaign_id'],
                insight_type=row['insight_type'],
                scope=row['scope'],
                summary=row['summary'],
                evidence_summary=row['evidence_summary'],
                reason_codes=row['reason_codes'],
                recommended_followup=row['recommended_followup'],
                recommendation_target=row['recommendation_target'],
                confidence=row['confidence'],
                metadata={**row['metadata'], 'run_id': run.id},
            )
        )

    pending_review_count = CampaignInsight.objects.filter(reviewed=False).count()
    recommendations: list[InsightRecommendation] = []
    for insight in created_insights:
        for row in build_insight_recommendations(insight=insight, pending_review_count=pending_review_count):
            recommendations.append(
                InsightRecommendation.objects.create(
                    insight_run=run,
                    target_campaign_id=row['target_campaign_id'],
                    campaign_insight_id=row['campaign_insight_id'],
                    recommendation_type=row['recommendation_type'],
                    insight_type=row['insight_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    run.candidate_count = len(candidates)
    run.lifecycle_closed_count = sum(1 for row in candidates if row.lifecycle_closed)
    run.insight_count = len(created_insights)
    run.success_pattern_count = sum(1 for row in created_insights if row.insight_type == InsightType.SUCCESS_PATTERN)
    run.failure_pattern_count = sum(1 for row in created_insights if row.insight_type == InsightType.FAILURE_PATTERN)
    run.blocker_pattern_count = sum(1 for row in created_insights if row.insight_type == InsightType.BLOCKER_PATTERN)
    run.governance_pattern_count = sum(1 for row in created_insights if row.insight_type == InsightType.GOVERNANCE_PATTERN)
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {
        'run': run,
        'candidates': candidates,
        'insights': created_insights,
        'recommendations': recommendations,
    }
