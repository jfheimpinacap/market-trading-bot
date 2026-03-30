from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.prediction_agent.models import PredictionAssessmentStatus, PredictionRuntimeAssessment
from apps.risk_agent.models import RiskRuntimeCandidate, RiskRuntimeRun


@dataclass
class CandidateBuildResult:
    candidates: list[RiskRuntimeCandidate]
    skipped_count: int


def _liquidity_bucket(liquidity_value: float) -> str:
    if liquidity_value < 10000:
        return 'poor'
    if liquidity_value < 40000:
        return 'thin'
    return 'good'


def build_runtime_candidates(*, runtime_run: RiskRuntimeRun) -> CandidateBuildResult:
    latest_assessments = (
        PredictionRuntimeAssessment.objects.select_related('linked_candidate__linked_market', 'linked_candidate__linked_market__provider')
        .filter(prediction_status__in=[PredictionAssessmentStatus.STRONG_EDGE, PredictionAssessmentStatus.WEAK_EDGE, PredictionAssessmentStatus.NEEDS_REVIEW])
        .order_by('-created_at', '-id')[:120]
    )

    candidates: list[RiskRuntimeCandidate] = []
    skipped = 0
    for assessment in latest_assessments:
        market = assessment.linked_candidate.linked_market
        if market is None:
            skipped += 1
            continue

        now = timezone.now()
        ttl_hours = None
        if market.close_time:
            delta = market.close_time - now
            if delta > timedelta(0):
                ttl_hours = int(delta.total_seconds() // 3600)
            else:
                ttl_hours = 0

        liquidity = float(market.liquidity or 0)
        volume = float(market.volume_24h or 0)
        spread_bps = int(market.spread_bps or 0)

        candidates.append(
            RiskRuntimeCandidate.objects.create(
                runtime_run=runtime_run,
                linked_prediction_assessment=assessment,
                linked_market=market,
                market_provider=market.provider.slug,
                category=market.category or assessment.linked_candidate.category,
                calibrated_probability=assessment.calibrated_probability,
                adjusted_edge=assessment.adjusted_edge,
                confidence_score=assessment.confidence_score,
                uncertainty_score=assessment.uncertainty_score,
                evidence_quality_score=assessment.evidence_quality_score,
                precedent_caution_score=assessment.precedent_caution_score,
                market_liquidity_context={
                    'bucket': _liquidity_bucket(liquidity),
                    'liquidity': liquidity,
                    'volume_24h': volume,
                    'spread_bps': spread_bps,
                },
                time_to_resolution=ttl_hours,
                predicted_status=assessment.prediction_status,
                metadata={
                    'paper_demo_only': True,
                    'prediction_runtime_run_id': assessment.linked_candidate.runtime_run_id,
                    'prediction_reason_codes': assessment.reason_codes,
                },
            )
        )

    return CandidateBuildResult(candidates=candidates, skipped_count=skipped)
