from __future__ import annotations

from decimal import Decimal

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseEvidenceStatus,
    BaselineResponseRecommendation,
    BaselineResponseRecommendationType,
    BaselineResponseRun,
    ResponseEvidencePack,
)


def build_response_recommendation(
    *,
    review_run: BaselineResponseRun,
    response_case: BaselineResponseCase,
    evidence_pack: ResponseEvidencePack,
) -> BaselineResponseRecommendation:
    mapping = {
        'KEEP_UNDER_WATCH': BaselineResponseRecommendationType.KEEP_UNDER_WATCH,
        'OPEN_REEVALUATION': BaselineResponseRecommendationType.OPEN_REEVALUATION,
        'OPEN_TUNING_REVIEW': BaselineResponseRecommendationType.OPEN_TUNING_REVIEW,
        'REQUIRE_MANUAL_BASELINE_REVIEW': BaselineResponseRecommendationType.REQUIRE_MANUAL_BASELINE_REVIEW,
        'PREPARE_ROLLBACK_REVIEW': BaselineResponseRecommendationType.PREPARE_ROLLBACK_REVIEW,
        'REQUIRE_COMMITTEE_RECHECK': BaselineResponseRecommendationType.REORDER_RESPONSE_PRIORITY,
    }

    recommendation_type = mapping.get(response_case.response_type, BaselineResponseRecommendationType.REORDER_RESPONSE_PRIORITY)
    confidence = Decimal(str(response_case.metadata.get('response_confidence', 0.55)))

    reason_codes = list(response_case.reason_codes or [])
    blockers = list(response_case.blockers or [])
    rationale = response_case.rationale

    if evidence_pack.evidence_status in {BaselineResponseEvidenceStatus.INSUFFICIENT, BaselineResponseEvidenceStatus.WEAK}:
        recommendation_type = BaselineResponseRecommendationType.REQUIRE_MORE_EVIDENCE
        rationale = f"Evidence is {evidence_pack.evidence_status.lower()} for current response pressure."
        if 'low_evidence_strength' not in reason_codes:
            reason_codes.append('low_evidence_strength')
        confidence = min(confidence, Decimal('0.45'))

    return BaselineResponseRecommendation.objects.create(
        review_run=review_run,
        target_case=response_case,
        recommendation_type=recommendation_type,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=confidence,
        blockers=blockers,
        metadata={
            'response_type': response_case.response_type,
            'evidence_status': evidence_pack.evidence_status,
            'manual_first': True,
        },
    )
