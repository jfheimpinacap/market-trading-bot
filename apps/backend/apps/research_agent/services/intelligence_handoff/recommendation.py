from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import (
    NarrativeConsensusRecommendation,
    NarrativeConsensusRecommendationType,
    ResearchHandoffStatus,
    ResearchPriorityBucket,
)


def build_consensus_recommendations(*, run, handoff_priorities):
    recommendations = []
    for handoff in handoff_priorities:
        rec_type = NarrativeConsensusRecommendationType.KEEP_ON_NARRATIVE_WATCHLIST
        blockers = []
        confidence = Decimal('0.6500')

        if handoff.handoff_status == ResearchHandoffStatus.BLOCKED:
            rec_type = NarrativeConsensusRecommendationType.BLOCK_FOR_CONFLICTED_NARRATIVE
            blockers = ['source_conflict']
            confidence = Decimal('0.8800')
        elif handoff.priority_bucket in {ResearchPriorityBucket.CRITICAL, ResearchPriorityBucket.HIGH}:
            if handoff.priority_reason_codes and 'high_market_divergence' in handoff.priority_reason_codes:
                rec_type = NarrativeConsensusRecommendationType.PRIORITIZE_FOR_MARKET_DIVERGENCE_REVIEW
            else:
                rec_type = NarrativeConsensusRecommendationType.SEND_TO_RESEARCH_IMMEDIATELY
            confidence = Decimal('0.8200')
        elif handoff.handoff_status == ResearchHandoffStatus.DEFERRED:
            rec_type = NarrativeConsensusRecommendationType.DEFER_FOR_WEAKER_SIGNAL
            confidence = Decimal('0.7000')

        if handoff.handoff_status == ResearchHandoffStatus.BLOCKED and 'conflicted_narrative' in handoff.priority_reason_codes:
            rec_type = NarrativeConsensusRecommendationType.REQUIRE_MANUAL_REVIEW_FOR_SOURCE_CONFLICT

        recommendation = NarrativeConsensusRecommendation.objects.create(
            consensus_run=run,
            recommendation_type=rec_type,
            target_cluster=handoff.linked_consensus_record.linked_cluster,
            target_market=handoff.linked_market,
            target_handoff=handoff,
            rationale=handoff.handoff_summary,
            reason_codes=handoff.priority_reason_codes,
            confidence=confidence,
            blockers=blockers,
        )
        recommendations.append(recommendation)
    return recommendations
