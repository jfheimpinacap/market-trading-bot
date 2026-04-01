from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import (
    AutonomousPositionWatchCandidate,
    AutonomousPositionWatchCandidateStatus,
    AutonomousSentimentState,
    AutonomousTradeExecution,
)
from apps.paper_trading.models import PaperPositionStatus, PaperTrade
from apps.portfolio_governor.models import PortfolioThrottleDecision
from apps.research_agent.models import MarketResearchCandidate, NarrativeSignal


def _portfolio_state() -> str:
    latest = PortfolioThrottleDecision.objects.order_by('-created_at_decision', '-id').first()
    return latest.state if latest else 'NORMAL'


def build_watch_candidates(*, watch_run) -> list[AutonomousPositionWatchCandidate]:
    pressure_state = _portfolio_state()
    positions = watch_run.metadata.get('open_position_ids')
    qs = watch_run.metadata.get('position_queryset')
    if qs is None:
        from apps.paper_trading.models import PaperPosition

        base = PaperPosition.objects.filter(status=PaperPositionStatus.OPEN, quantity__gt=0).select_related('market', 'account')
        if positions:
            base = base.filter(id__in=positions)
        qs = base

    created: list[AutonomousPositionWatchCandidate] = []
    for position in qs.order_by('-updated_at', '-id'):
        latest_trade = PaperTrade.objects.filter(position=position).order_by('-executed_at', '-id').first()
        linked_execution = None
        entry_probability = None
        entry_edge = None
        if latest_trade:
            linked_execution = (
                AutonomousTradeExecution.objects.select_related('linked_candidate')
                .filter(linked_paper_trade__position=position)
                .order_by('-created_at', '-id')
                .first()
            )
            if linked_execution and linked_execution.linked_candidate:
                entry_probability = linked_execution.linked_candidate.system_probability
                entry_edge = linked_execution.linked_candidate.adjusted_edge

        signal = NarrativeSignal.objects.filter(linked_market=position.market).order_by('-created_at_scan', '-id').first()
        research = MarketResearchCandidate.objects.filter(linked_market=position.market).order_by('-created_at', '-id').first()

        sentiment_state = AutonomousSentimentState.UNKNOWN
        current_probability = entry_probability
        current_edge = entry_edge
        if signal:
            score = Decimal(str(signal.sentiment_score or '0'))
            current_probability = Decimal('0.5000') + (score / Decimal('2'))
            current_probability = max(Decimal('0.0000'), min(Decimal('1.0000'), current_probability))
            current_edge = Decimal(str(signal.total_signal_score or '0')) - Decimal('0.5000')
            if score >= Decimal('0.20'):
                sentiment_state = AutonomousSentimentState.IMPROVING
            elif score <= Decimal('-0.20'):
                sentiment_state = AutonomousSentimentState.REVERSING
            elif score < Decimal('-0.05'):
                sentiment_state = AutonomousSentimentState.WEAKENING
            else:
                sentiment_state = AutonomousSentimentState.STABLE

        created.append(
            AutonomousPositionWatchCandidate.objects.create(
                linked_watch_run=watch_run,
                linked_position=position,
                linked_paper_trade=latest_trade,
                linked_autonomous_execution=linked_execution,
                linked_market=position.market,
                linked_latest_scan_signal=signal,
                linked_latest_research_context=research,
                candidate_status=AutonomousPositionWatchCandidateStatus.ACTIVE_MONITORING,
                entry_probability=entry_probability,
                current_probability=current_probability,
                entry_edge=entry_edge,
                current_edge=current_edge,
                sentiment_state=sentiment_state,
                portfolio_pressure_state=pressure_state,
                metadata={'paper_only': True},
            )
        )
    return created
