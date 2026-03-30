from __future__ import annotations

from decimal import Decimal

from apps.experiment_lab.models import ChampionChallengerComparisonStatus
from apps.promotion_committee.models import PromotionCase, PromotionEvidencePack, PromotionEvidenceStatus


def _evidence_status(*, sample_count: int, confidence: float, comparison_status: str) -> str:
    if sample_count < 30 or comparison_status == ChampionChallengerComparisonStatus.NEEDS_MORE_DATA:
        return PromotionEvidenceStatus.INSUFFICIENT
    if comparison_status == ChampionChallengerComparisonStatus.INCONCLUSIVE:
        return PromotionEvidenceStatus.WEAK
    if comparison_status == ChampionChallengerComparisonStatus.MIXED or confidence < 0.55:
        return PromotionEvidenceStatus.MIXED
    if comparison_status == ChampionChallengerComparisonStatus.IMPROVED and confidence >= 0.70:
        return PromotionEvidenceStatus.STRONG
    return PromotionEvidenceStatus.WEAK


def build_evidence_pack(*, promotion_case: PromotionCase):
    comparison = promotion_case.linked_comparison
    recommendation = promotion_case.metadata.get('promotion_recommendation_type')
    sample_count = int(comparison.sample_count if comparison else 0)
    confidence = float(comparison.confidence_score if comparison else 0)
    comparison_status = comparison.comparison_status if comparison else ChampionChallengerComparisonStatus.INCONCLUSIVE

    benefit_score = confidence if comparison_status == ChampionChallengerComparisonStatus.IMPROVED else max(confidence - 0.3, 0.0)
    risk_score = 1.0 - confidence
    if promotion_case.target_scope == 'global':
        risk_score = min(1.0, risk_score + 0.15)

    status = _evidence_status(sample_count=sample_count, confidence=confidence, comparison_status=comparison_status)

    return PromotionEvidencePack.objects.create(
        linked_promotion_case=promotion_case,
        summary=f"{comparison_status} comparison with sample_count={sample_count} and confidence={confidence:.2f}.",
        linked_metrics=comparison.compared_metrics if comparison else {},
        linked_comparisons={
            'comparison_id': comparison.id if comparison else None,
            'comparison_status': comparison_status,
            'baseline_label': comparison.baseline_label if comparison else None,
            'challenger_label': comparison.challenger_label if comparison else None,
        },
        linked_recommendations={'experiment_recommendation_type': recommendation},
        sample_count=sample_count,
        confidence_score=Decimal(str(round(confidence, 4))),
        risk_of_adoption_score=Decimal(str(round(risk_score, 4))),
        expected_benefit_score=Decimal(str(round(benefit_score, 4))),
        evidence_status=status,
        metadata={'comparison_reason_codes': comparison.reason_codes if comparison else []},
    )
