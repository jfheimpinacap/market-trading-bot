from __future__ import annotations

from dataclasses import dataclass

from apps.learning_memory.models import LearningAdjustment
from apps.operator_queue.models import OperatorQueueItem
from apps.postmortem_demo.models import TradeReview
from apps.prediction_agent.models import PredictionScore
from apps.research_agent.models import ResearchCandidate
from apps.risk_agent.models import PositionWatchEvent, RiskAssessment, RiskSizingDecision
from apps.runtime_governor.models import RuntimeModeState, RuntimeTransitionLog
from apps.safety_guard.models import SafetyEvent


@dataclass
class PostmortemBoardContext:
    review: TradeReview
    research_candidate: ResearchCandidate | None
    prediction_score: PredictionScore | None
    risk_assessment: RiskAssessment | None
    risk_sizing: RiskSizingDecision | None
    watch_events: list[PositionWatchEvent]
    runtime_state: RuntimeModeState | None
    runtime_transitions: list[RuntimeTransitionLog]
    safety_events: list[SafetyEvent]
    operator_items: list[OperatorQueueItem]
    recent_learning_adjustments: list[LearningAdjustment]


def build_board_context(review: TradeReview) -> PostmortemBoardContext:
    trade = review.paper_trade
    research_candidate = ResearchCandidate.objects.filter(market_id=review.market_id).order_by('-updated_at', '-id').first()
    prediction_score = PredictionScore.objects.filter(market_id=review.market_id).order_by('-created_at', '-id').first()
    risk_assessment = RiskAssessment.objects.filter(market_id=review.market_id).order_by('-created_at', '-id').first()
    risk_sizing = (
        RiskSizingDecision.objects.filter(risk_assessment=risk_assessment).order_by('-created_at', '-id').first()
        if risk_assessment
        else None
    )
    watch_events = list(
        PositionWatchEvent.objects.filter(paper_position__market_id=review.market_id)
        .order_by('-created_at', '-id')[:5]
    )
    runtime_state = RuntimeModeState.objects.order_by('-effective_at', '-id').first()
    runtime_transitions = list(RuntimeTransitionLog.objects.order_by('-created_at', '-id')[:5])
    safety_events = list(
        SafetyEvent.objects.filter(related_trade_id=trade.id).order_by('-created_at', '-id')[:5]
    )
    operator_items = list(
        OperatorQueueItem.objects.filter(related_trade_id=trade.id).order_by('-created_at', '-id')[:5]
    )
    recent_learning_adjustments = list(LearningAdjustment.objects.filter(is_active=True).order_by('-updated_at', '-id')[:5])

    return PostmortemBoardContext(
        review=review,
        research_candidate=research_candidate,
        prediction_score=prediction_score,
        risk_assessment=risk_assessment,
        risk_sizing=risk_sizing,
        watch_events=watch_events,
        runtime_state=runtime_state,
        runtime_transitions=runtime_transitions,
        safety_events=safety_events,
        operator_items=operator_items,
        recent_learning_adjustments=recent_learning_adjustments,
    )
