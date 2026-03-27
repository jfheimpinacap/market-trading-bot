from __future__ import annotations

from dataclasses import dataclass

from apps.promotion_committee.models import PromotionRecommendationCode, StackEvidenceSnapshot


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
