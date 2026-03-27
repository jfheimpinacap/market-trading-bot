from __future__ import annotations

from decimal import Decimal

from apps.champion_challenger.models import ChallengerRecommendationCode


MIN_SAMPLE_PROPOSALS = 5


def _d(value: object) -> Decimal:
    return Decimal(str(value or '0'))


def generate_recommendation(*, comparison: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    deltas = comparison['deltas']
    champion = comparison['champion_metrics']
    challenger = comparison['challenger_metrics']

    if min(champion['proposal_ready_count'], challenger['proposal_ready_count']) < MIN_SAMPLE_PROPOSALS:
        return ChallengerRecommendationCode.REVIEW_MANUALLY, ['insufficient sample size for reliable benchmark']

    pnl_delta = _d(deltas['execution_adjusted_pnl_delta'])
    drawdown_delta = Decimal(str(deltas['drawdown_proxy_delta']))
    fill_delta = Decimal(str(deltas['fill_rate_delta']))
    divergence = Decimal(str(comparison['decision_divergence_rate']))

    if pnl_delta > 0:
        reasons.append('better execution-adjusted pnl')
    if drawdown_delta < 0:
        reasons.append('lower drawdown proxy')
    if fill_delta > 0:
        reasons.append('better fill rate')
    if deltas['risk_review_pressure_delta'] > 0.15:
        reasons.append('too much queue/review pressure')

    if pnl_delta > 0 and drawdown_delta <= 0 and fill_delta >= Decimal('-0.02'):
        return ChallengerRecommendationCode.CHALLENGER_PROMISING, reasons or ['challenger outperforms champion on key metrics']

    if pnl_delta < 0 and (drawdown_delta > 0 or fill_delta < 0):
        reasons.append('worse execution-adjusted pnl')
        return ChallengerRecommendationCode.CHALLENGER_UNDERPERFORMS, reasons

    if divergence > Decimal('0.45') and pnl_delta <= 0:
        reasons.append('high divergence with no performance gain')
        return ChallengerRecommendationCode.KEEP_CHAMPION, reasons

    return ChallengerRecommendationCode.KEEP_CHAMPION, reasons or ['champion remains more stable']
