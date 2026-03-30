from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.promotion_committee.models import PromotionRecommendationCode, StackEvidenceSnapshot
from apps.promotion_committee.models import (
    PromotionCase,
    PromotionCaseStatus,
    PromotionDecisionRecommendation,
    PromotionDecisionRecommendationType,
    PromotionEvidencePack,
    PromotionReviewCycleRun,
)


@dataclass
class RecommendationResult:
    code: str
    rationale: str
    reason_codes: list[str]
    blocking_constraints: list[str]
    confidence: float
    evidence_summary: dict


def generate_recommendation(snapshot: StackEvidenceSnapshot) -> RecommendationResult:
    readiness_status = snapshot.readiness_summary.get('status', 'UNKNOWN')
    sample = snapshot.champion_challenger_summary.get('sample_size', {})
    markets = int(sample.get('markets_evaluated', 0) or 0)

    pnl_delta = float(snapshot.execution_aware_metrics.get('pnl_delta_execution_adjusted') or 0)
    fill_delta = float(snapshot.execution_aware_metrics.get('fill_rate_delta') or 0)
    no_fill_delta = float(snapshot.execution_aware_metrics.get('no_fill_rate_delta') or 0)
    drag_delta = float(snapshot.execution_aware_metrics.get('execution_drag_delta') or 0)
    drawdown_delta = float(snapshot.execution_aware_metrics.get('drawdown_proxy_delta') or 0)
    queue_pressure_delta = float(snapshot.execution_aware_metrics.get('queue_pressure_delta') or 0)

    throttle_state = snapshot.portfolio_governor_context.get('throttle_state', 'UNKNOWN')
    blockers: list[str] = []
    reasons: list[str] = []

    if readiness_status == 'NOT_READY':
        blockers.append('READINESS_NOT_READY')
    if throttle_state in {'BLOCK_NEW_ENTRIES', 'FORCE_REDUCE'}:
        blockers.append('PORTFOLIO_STRESS_BLOCK')

    if blockers:
        return RecommendationResult(
            code=PromotionRecommendationCode.REVERT_TO_CONSERVATIVE_STACK,
            rationale='Readiness or portfolio stress constraints block promotion; conservative posture is required.',
            reason_codes=['SAFETY_FIRST', *blockers],
            blocking_constraints=blockers,
            confidence=0.93,
            evidence_summary={
                'readiness_status': readiness_status,
                'throttle_state': throttle_state,
                'execution_aware_metrics': snapshot.execution_aware_metrics,
            },
        )

    if markets < 10:
        reasons.append('INSUFFICIENT_SAMPLE_SIZE')
        return RecommendationResult(
            code=PromotionRecommendationCode.EXTEND_SHADOW_TEST,
            rationale='Evidence is promising but sample size is still small for auditable promotion.',
            reason_codes=reasons,
            blocking_constraints=[],
            confidence=0.62,
            evidence_summary={'markets_evaluated': markets, 'execution_aware_metrics': snapshot.execution_aware_metrics},
        )

    degraded_execution = pnl_delta < 0 or fill_delta < -0.02 or no_fill_delta > 0.02 or drag_delta > 0.02 or drawdown_delta > 0.02
    if degraded_execution:
        reasons.extend(['EXECUTION_AWARE_DETERIORATION'])
        return RecommendationResult(
            code=PromotionRecommendationCode.KEEP_CURRENT_CHAMPION,
            rationale='Execution-aware results deteriorated under challenger conditions; keep current champion.',
            reason_codes=reasons,
            blocking_constraints=[],
            confidence=0.88,
            evidence_summary=snapshot.execution_aware_metrics,
        )

    if readiness_status == 'CAUTION':
        reasons.extend(['READINESS_CAUTION'])
        return RecommendationResult(
            code=PromotionRecommendationCode.EXTEND_SHADOW_TEST,
            rationale='Readiness is in caution mode; extend shadow test before any stack promotion.',
            reason_codes=reasons,
            blocking_constraints=[],
            confidence=0.74,
            evidence_summary=snapshot.execution_aware_metrics,
        )

    if pnl_delta > 0 and fill_delta >= 0 and no_fill_delta <= 0 and drawdown_delta <= 0 and queue_pressure_delta <= 0.03:
        reasons.extend(['EXECUTION_AWARE_IMPROVEMENT', 'READINESS_READY'])
        return RecommendationResult(
            code=PromotionRecommendationCode.PROMOTE_CHALLENGER,
            rationale='Challenger shows positive execution-aware improvements with readiness READY and no critical blockers.',
            reason_codes=reasons,
            blocking_constraints=[],
            confidence=0.9,
            evidence_summary=snapshot.execution_aware_metrics,
        )

    return RecommendationResult(
        code=PromotionRecommendationCode.MANUAL_REVIEW_REQUIRED,
        rationale='Evidence is mixed; operator review is required before changing stack bindings.',
        reason_codes=['MIXED_SIGNALS'],
        blocking_constraints=[],
        confidence=0.55,
        evidence_summary=snapshot.execution_aware_metrics,
    )


def _base_recommendation(case: PromotionCase, evidence: PromotionEvidencePack) -> tuple[str, str, list[str], float]:
    if case.case_status == PromotionCaseStatus.NEEDS_MORE_DATA:
        return (
            PromotionDecisionRecommendationType.DEFER_FOR_MORE_EVIDENCE,
            'Validation is inconclusive or sample size is insufficient for committee-ready manual adoption.',
            ['needs_more_data'],
            0.76,
        )
    if case.case_status == PromotionCaseStatus.REJECTED:
        return (
            PromotionDecisionRecommendationType.REJECT_CHANGE,
            'Challenger degrades key metrics versus baseline in current validation evidence.',
            ['degraded_metrics'],
            0.86,
        )
    if case.case_status == PromotionCaseStatus.DEFERRED:
        return (
            PromotionDecisionRecommendationType.SPLIT_SCOPE_AND_RETEST,
            'Evidence is mixed or overly broad for current scope; split scope and retest before adoption.',
            ['mixed_signals_or_scope_too_broad'],
            0.68,
        )

    if float(evidence.risk_of_adoption_score) > 0.45:
        return (
            PromotionDecisionRecommendationType.REQUIRE_COMMITTEE_REVIEW,
            'Expected uplift is promising but adoption risk remains elevated; require explicit committee review.',
            ['elevated_adoption_risk'],
            0.72,
        )

    return (
        PromotionDecisionRecommendationType.APPROVE_FOR_MANUAL_ADOPTION,
        'Evidence is strong with clear expected benefit and acceptable adoption risk for manual-first approval.',
        ['strong_evidence'],
        0.82,
    )


def create_case_recommendation(*, review_run: PromotionReviewCycleRun, case: PromotionCase, evidence_pack: PromotionEvidencePack):
    recommendation_type, rationale, reason_codes, confidence = _base_recommendation(case, evidence_pack)
    return PromotionDecisionRecommendation.objects.create(
        review_run=review_run,
        target_case=case,
        recommendation_type=recommendation_type,
        rationale=rationale,
        reason_codes=[*reason_codes, *case.reason_codes],
        confidence=Decimal(str(confidence)),
        blockers=case.blockers,
        metadata={'evidence_status': evidence_pack.evidence_status},
    )


def create_grouping_recommendation(*, review_run: PromotionReviewCycleRun, grouped_case_ids: list[int]):
    if len(grouped_case_ids) < 2:
        return None
    return PromotionDecisionRecommendation.objects.create(
        review_run=review_run,
        target_case=None,
        recommendation_type=PromotionDecisionRecommendationType.GROUP_WITH_RELATED_CHANGES,
        rationale='Multiple cases target the same component/scope; review as a bounded grouped package.',
        reason_codes=['related_changes_detected'],
        confidence=Decimal('0.64'),
        blockers=[],
        metadata={'grouped_case_ids': grouped_case_ids},
    )


def create_reorder_recommendation(*, review_run: PromotionReviewCycleRun, high_priority_case_ids: list[int]):
    if len(high_priority_case_ids) < 2:
        return None
    return PromotionDecisionRecommendation.objects.create(
        review_run=review_run,
        target_case=None,
        recommendation_type=PromotionDecisionRecommendationType.REORDER_PROMOTION_PRIORITY,
        rationale='Several high-priority cases are ready; enforce explicit ordering before manual adoption meetings.',
        reason_codes=['multiple_high_priority_cases'],
        confidence=Decimal('0.67'),
        blockers=[],
        metadata={'prioritized_case_ids': high_priority_case_ids},
    )
