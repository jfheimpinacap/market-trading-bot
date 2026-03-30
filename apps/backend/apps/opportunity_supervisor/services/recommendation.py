from __future__ import annotations

from decimal import Decimal

from apps.opportunity_supervisor.models import (
    OpportunityFusionAssessment,
    OpportunityRecommendation,
    OpportunityRecommendationType,
    PaperOpportunityProposal,
)


def create_recommendations(*, assessment: OpportunityFusionAssessment, proposal: PaperOpportunityProposal) -> list[OpportunityRecommendation]:
    items: list[OpportunityRecommendation] = []

    if assessment.fusion_status == 'READY_FOR_PROPOSAL':
        items.append(
            OpportunityRecommendation.objects.create(
                runtime_run=assessment.runtime_run,
                target_assessment=assessment,
                recommendation_type=OpportunityRecommendationType.SEND_TO_PROPOSAL_ENGINE,
                rationale='Opportunity cleared fusion gating and is ready for paper proposal workflow.',
                reason_codes=assessment.reason_codes,
                confidence=assessment.final_opportunity_score,
                blockers=assessment.blockers,
            )
        )
        if proposal.execution_sim_recommended:
            items.append(
                OpportunityRecommendation.objects.create(
                    runtime_run=assessment.runtime_run,
                    target_assessment=assessment,
                    recommendation_type=OpportunityRecommendationType.SEND_TO_EXECUTION_SIMULATOR,
                    rationale='High final opportunity score supports a paper execution simulation handoff.',
                    reason_codes=['execution_sim_recommended'],
                    confidence=min(Decimal('1.0000'), assessment.final_opportunity_score + Decimal('0.0500')),
                    blockers=[],
                )
            )
    elif assessment.fusion_status == 'WATCH_ONLY':
        items.append(
            OpportunityRecommendation.objects.create(
                runtime_run=assessment.runtime_run,
                target_assessment=assessment,
                recommendation_type=OpportunityRecommendationType.KEEP_ON_WATCH,
                rationale='Signal appears interesting but does not meet proposal readiness thresholds.',
                reason_codes=assessment.reason_codes,
                confidence=assessment.final_opportunity_score,
                blockers=assessment.blockers,
            )
        )
    elif assessment.fusion_status == 'BLOCKED_BY_RISK':
        items.append(
            OpportunityRecommendation.objects.create(
                runtime_run=assessment.runtime_run,
                target_assessment=assessment,
                recommendation_type=OpportunityRecommendationType.BLOCK_BY_RISK,
                rationale='Risk runtime blocked this opportunity.',
                reason_codes=assessment.reason_codes,
                confidence=Decimal('0.9000'),
                blockers=assessment.blockers,
            )
        )
    elif assessment.fusion_status == 'BLOCKED_BY_LEARNING':
        items.append(
            OpportunityRecommendation.objects.create(
                runtime_run=assessment.runtime_run,
                target_assessment=assessment,
                recommendation_type=OpportunityRecommendationType.BLOCK_BY_LEARNING,
                rationale='Active learning cautions exceed safe threshold.',
                reason_codes=assessment.reason_codes,
                confidence=Decimal('0.8500'),
                blockers=assessment.blockers,
            )
        )
    elif assessment.fusion_status == 'LOW_CONVICTION':
        items.append(
            OpportunityRecommendation.objects.create(
                runtime_run=assessment.runtime_run,
                target_assessment=assessment,
                recommendation_type=OpportunityRecommendationType.BLOCK_LOW_CONVICTION,
                rationale='Edge/confidence mix is not sufficient for proposal handoff.',
                reason_codes=assessment.reason_codes,
                confidence=Decimal('0.7000'),
                blockers=assessment.blockers,
            )
        )
    else:
        items.append(
            OpportunityRecommendation.objects.create(
                runtime_run=assessment.runtime_run,
                target_assessment=assessment,
                recommendation_type=OpportunityRecommendationType.REQUIRE_MANUAL_OPPORTUNITY_REVIEW,
                rationale='Fusion outcome requires manual review before any downstream handoff.',
                reason_codes=assessment.reason_codes,
                confidence=Decimal('0.6000'),
                blockers=assessment.blockers,
            )
        )

    return items
