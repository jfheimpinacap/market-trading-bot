from __future__ import annotations

from decimal import Decimal

from apps.certification_board.models import (
    BaselineHealthRecommendation,
    BaselineHealthRecommendationType,
    BaselineHealthStatus,
    BaselineHealthStatusCode,
)


def build_baseline_health_recommendation(*, review_run, status: BaselineHealthStatus) -> BaselineHealthRecommendation:
    code = status.health_status
    if code == BaselineHealthStatusCode.HEALTHY:
        rec_type = BaselineHealthRecommendationType.KEEP_BASELINE_ACTIVE
        confidence = Decimal('0.82')
        rationale = 'Baseline remains healthy under recent calibration/risk/opportunity evidence.'
    elif code in {BaselineHealthStatusCode.INSUFFICIENT_DATA, BaselineHealthStatusCode.UNDER_WATCH}:
        rec_type = BaselineHealthRecommendationType.KEEP_UNDER_WATCH
        confidence = Decimal('0.66')
        rationale = 'Keep baseline active but under watch until evidence density improves.'
    elif code == BaselineHealthStatusCode.DEGRADED:
        rec_type = BaselineHealthRecommendationType.OPEN_TUNING_REVIEW
        confidence = Decimal('0.78')
        rationale = 'Baseline shows degradation signals; open bounded tuning review.'
    elif code == BaselineHealthStatusCode.ROLLBACK_REVIEW_RECOMMENDED:
        rec_type = BaselineHealthRecommendationType.PREPARE_ROLLBACK_REVIEW
        confidence = Decimal('0.9')
        rationale = 'Degradation pressure is severe enough to prepare manual rollback review.'
    else:
        rec_type = BaselineHealthRecommendationType.REQUIRE_REEVALUATION
        confidence = Decimal('0.74')
        rationale = 'Health state requires manual re-evaluation before continuing unchanged.'

    if status.linked_candidate.target_scope == 'global' and rec_type in {
        BaselineHealthRecommendationType.REQUIRE_REEVALUATION,
        BaselineHealthRecommendationType.OPEN_TUNING_REVIEW,
    }:
        rec_type = BaselineHealthRecommendationType.REQUIRE_MANUAL_BASELINE_REVIEW
        rationale = 'Global-scope baseline has mixed risk signals and requires manual committee review.'

    return BaselineHealthRecommendation.objects.create(
        review_run=review_run,
        target_status=status,
        recommendation_type=rec_type,
        rationale=rationale,
        reason_codes=status.reason_codes,
        confidence=confidence,
        blockers=status.blockers,
        metadata={
            'health_status': status.health_status,
            'target_component': status.linked_candidate.target_component,
            'target_scope': status.linked_candidate.target_scope,
        },
    )
