from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import NarrativeSignal, ScanRecommendationType


def recommend_for_signal(signal: NarrativeSignal) -> tuple[str, Decimal, list[str], list[str], str]:
    reason_codes = list(signal.reason_codes or [])
    blockers: list[str] = []

    if signal.total_signal_score >= Decimal('0.7800') and signal.market_divergence_score >= Decimal('0.2500'):
        return ScanRecommendationType.SEND_TO_RESEARCH_TRIAGE, Decimal('0.8400'), reason_codes + ['EDGE_CANDIDATE'], blockers, 'Strong narrative edge against market context.'

    if signal.total_signal_score >= Decimal('0.6800') and signal.direction in {'bullish_yes', 'bearish_yes'}:
        return ScanRecommendationType.SEND_TO_PREDICTION_CONTEXT, Decimal('0.7600'), reason_codes + ['PREDICTION_CONTEXT_READY'], blockers, 'Signal is coherent enough for prediction context.'

    if signal.status == 'ignore' or signal.total_signal_score < Decimal('0.4500'):
        return ScanRecommendationType.IGNORE_NOISE, Decimal('0.7000'), reason_codes + ['LOW_SIGNAL_QUALITY'], blockers, 'Signal classified as noisy/low quality.'

    if signal.direction in {'mixed', 'unclear'}:
        blockers.append('direction_unclear')
        return ScanRecommendationType.REQUIRE_MANUAL_REVIEW, Decimal('0.6200'), reason_codes + ['MANUAL_REVIEW_REQUIRED'], blockers, 'Narrative direction is not clear enough.'

    return ScanRecommendationType.KEEP_ON_WATCHLIST, Decimal('0.6400'), reason_codes + ['WATCH_AND_RESCAN'], blockers, 'Keep signal on watchlist for convergence confirmation.'
