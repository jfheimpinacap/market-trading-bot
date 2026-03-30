from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.markets.models import Market
from apps.prediction_agent.models import PredictionRuntimeCandidate, PredictionRuntimeRun
from apps.research_agent.models import MarketResearchCandidate, MarketResearchCandidateStatus


@dataclass
class CandidateBuildResult:
    candidates: list[PredictionRuntimeCandidate]
    blocked_count: int


def _safe_decimal(value: Decimal | None, default: str = '0.0000') -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def build_runtime_candidates(*, runtime_run: PredictionRuntimeRun, limit: int = 40) -> CandidateBuildResult:
    research_candidates = (
        MarketResearchCandidate.objects.select_related('linked_market')
        .filter(status__in=[MarketResearchCandidateStatus.SHORTLIST, MarketResearchCandidateStatus.WATCHLIST])
        .order_by('-pursue_worthiness_score', '-created_at')[:limit]
    )

    created: list[PredictionRuntimeCandidate] = []
    blocked_count = 0
    for research_candidate in research_candidates:
        market: Market = research_candidate.linked_market
        market_probability = market.current_market_probability
        if market_probability is None:
            blocked_count += 1
            continue

        quality_score = (
            (_safe_decimal(research_candidate.market_quality_score) * Decimal('0.45'))
            + (_safe_decimal(research_candidate.narrative_support_score) * Decimal('0.25'))
            + (_safe_decimal(research_candidate.freshness_score) * Decimal('0.20'))
            + (_safe_decimal(research_candidate.liquidity_score) * Decimal('0.10'))
        )

        candidate = PredictionRuntimeCandidate.objects.create(
            runtime_run=runtime_run,
            linked_market=market,
            linked_research_candidate=research_candidate,
            linked_scan_signals=research_candidate.linked_narrative_signals or [],
            market_provider=research_candidate.market_provider,
            category=research_candidate.category,
            market_probability=market_probability,
            narrative_support_score=research_candidate.narrative_support_score,
            divergence_score=research_candidate.divergence_score,
            research_status=research_candidate.status,
            candidate_quality_score=quality_score.quantize(Decimal('0.0001')),
            metadata={
                'triage_reason_codes': research_candidate.reason_codes,
                'triage_rationale': research_candidate.rationale,
            },
        )
        created.append(candidate)

    return CandidateBuildResult(candidates=created, blocked_count=blocked_count)
