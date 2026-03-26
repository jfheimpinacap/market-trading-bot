from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount
from apps.proposal_engine.models import ProposalStatus, TradeProposal
from apps.proposal_engine.services.context import build_proposal_context
from apps.proposal_engine.services.heuristics import evaluate_proposal_heuristics


def generate_trade_proposal(*, market: Market, paper_account: PaperAccount | None = None, triggered_from: str = 'market_detail') -> TradeProposal:
    context = build_proposal_context(market=market, paper_account=paper_account)
    result = evaluate_proposal_heuristics(context=context, triggered_from=triggered_from)

    expires_at = timezone.now() + timedelta(hours=6)

    return TradeProposal.objects.create(
        market=market,
        paper_account=context.paper_account,
        proposal_status=ProposalStatus.ACTIVE,
        direction=result.direction,
        proposal_score=result.proposal_score,
        confidence=result.confidence,
        headline=result.headline,
        thesis=result.thesis,
        rationale=result.rationale,
        suggested_trade_type=result.suggested_trade_type,
        suggested_side=result.suggested_side,
        suggested_quantity=result.suggested_quantity,
        suggested_price_reference=result.suggested_price_reference,
        risk_decision=result.risk_assessment.decision,
        policy_decision=result.policy_decision.decision,
        approval_required=result.approval_required,
        is_actionable=result.is_actionable,
        recommendation=result.recommendation,
        expires_at=expires_at,
        metadata={
            'triggered_from': triggered_from,
            'signals': {
                'count': len(context.latest_signals),
                'actionable': context.actionable_signal_count,
                'bullish': context.bullish_count,
                'bearish': context.bearish_count,
                'neutral': context.neutral_count,
            },
            'paper_account': {
                'id': context.paper_account.id if context.paper_account else None,
                'cash_balance': str(context.cash_balance),
                'market_exposure_quantity': str(context.market_exposure_quantity),
                'market_exposure_value': str(context.market_exposure_value),
            },
            'risk_assessment_id': result.risk_assessment.id,
            'risk_agent_assessment_id': result.risk_assessment.metadata.get('risk_agent_assessment_id'),
            'risk_agent_sizing_id': result.risk_assessment.metadata.get('risk_agent_sizing_id'),
            'policy_decision_id': result.policy_decision.id,
            'prediction': {
                'id': context.latest_prediction_score.id if context.latest_prediction_score else None,
                'system_probability': str(context.latest_prediction_score.system_probability) if context.latest_prediction_score else None,
                'market_probability': str(context.latest_prediction_score.market_probability) if context.latest_prediction_score else None,
                'edge': str(context.latest_prediction_score.edge) if context.latest_prediction_score else None,
                'confidence': str(context.latest_prediction_score.confidence) if context.latest_prediction_score else None,
                'profile': context.latest_prediction_score.model_profile_used if context.latest_prediction_score else None,
            },
        },
    )
