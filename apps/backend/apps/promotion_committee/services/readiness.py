from __future__ import annotations

from apps.experiment_lab.models import ChampionChallengerComparisonStatus
from apps.promotion_committee.models import PromotionCase, PromotionCaseStatus, PromotionEvidencePack


def classify_case_readiness(*, promotion_case: PromotionCase, evidence_pack: PromotionEvidencePack) -> str:
    comparison_status = promotion_case.metadata.get('comparison_status')
    if comparison_status in {
        ChampionChallengerComparisonStatus.INCONCLUSIVE,
        ChampionChallengerComparisonStatus.NEEDS_MORE_DATA,
    }:
        return PromotionCaseStatus.NEEDS_MORE_DATA

    if evidence_pack.evidence_status == 'INSUFFICIENT':
        return PromotionCaseStatus.NEEDS_MORE_DATA

    if comparison_status == ChampionChallengerComparisonStatus.DEGRADED:
        return PromotionCaseStatus.REJECTED

    if comparison_status == ChampionChallengerComparisonStatus.MIXED:
        return PromotionCaseStatus.DEFERRED

    if promotion_case.target_scope == 'global' and evidence_pack.sample_count < 80:
        return PromotionCaseStatus.DEFERRED

    return PromotionCaseStatus.READY_FOR_REVIEW
