from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import AutonomousPortfolioPressureState, AutonomousRiskState, AutonomousSentimentState
from apps.risk_agent.models import RiskRuntimeRecommendation


def assess_candidate(candidate) -> dict:
    reason_codes: list[str] = []
    severity = 'INFO'

    latest_risk = RiskRuntimeRecommendation.objects.filter(target_candidate__linked_market=candidate.linked_market).order_by('-created_at', '-id').first()
    risk_state = AutonomousRiskState.NORMAL
    if latest_risk:
        if latest_risk.recommendation_type.startswith('BLOCK_'):
            risk_state = AutonomousRiskState.BLOCKED
            reason_codes.append('RISK_BLOCKED')
        elif latest_risk.recommendation_type in {'REQUIRE_MANUAL_RISK_REVIEW'}:
            risk_state = AutonomousRiskState.ELEVATED
            reason_codes.append('RISK_REVIEW_REQUIRED')
        elif latest_risk.recommendation_type in {'APPROVE_REDUCED_SIZE', 'KEEP_ON_WATCH'}:
            risk_state = AutonomousRiskState.CAUTION
            reason_codes.append('RISK_CAUTION')

    candidate.risk_state = risk_state

    entry_edge = Decimal(str(candidate.entry_edge or '0'))
    current_edge = Decimal(str(candidate.current_edge or entry_edge))
    edge_delta = current_edge - entry_edge
    if edge_delta <= Decimal('-0.1500'):
        reason_codes.append('EDGE_DECAY_CRITICAL')
        severity = 'CRITICAL'
    elif edge_delta <= Decimal('-0.0600'):
        reason_codes.append('EDGE_DECAY')
        severity = 'ACTIONABLE'

    if candidate.sentiment_state == AutonomousSentimentState.REVERSING:
        reason_codes.append('NARRATIVE_REVERSAL')
        severity = 'CRITICAL'
    elif candidate.sentiment_state == AutonomousSentimentState.WEAKENING:
        reason_codes.append('SENTIMENT_WEAKENING')
        severity = 'ACTIONABLE' if severity == 'INFO' else severity

    if candidate.portfolio_pressure_state in {
        AutonomousPortfolioPressureState.THROTTLED,
        AutonomousPortfolioPressureState.BLOCK_NEW_ENTRIES,
    }:
        reason_codes.append('PORTFOLIO_PRESSURE')
        severity = 'ACTIONABLE' if severity == 'INFO' else severity

    candidate.save(update_fields=['risk_state', 'updated_at'])
    return {
        'severity': severity,
        'reason_codes': reason_codes,
        'edge_delta': str(edge_delta),
    }
