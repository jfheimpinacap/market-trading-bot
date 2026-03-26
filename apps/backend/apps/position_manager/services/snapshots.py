from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.paper_trading.models import PaperPosition
from apps.prediction_agent.models import PredictionScore
from apps.research_agent.models import ResearchCandidate
from apps.risk_agent.models import PositionWatchEvent
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status


def _to_decimal(value, default: str = '0') -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def build_position_snapshot(position: PaperPosition) -> tuple[dict, PredictionScore | None, PositionWatchEvent | None]:
    latest_prediction = PredictionScore.objects.filter(market=position.market).order_by('-created_at', '-id').first()
    latest_watch_event = PositionWatchEvent.objects.filter(paper_position=position).order_by('-created_at', '-id').first()
    research_candidate = ResearchCandidate.objects.filter(market=position.market).order_by('-updated_at', '-id').first()

    entry_probability = _to_decimal(position.metadata.get('entry_market_probability', position.average_entry_price / Decimal('100')))
    current_market_probability = _to_decimal(position.market.current_market_probability, '0.5')
    prediction_probability = _to_decimal(latest_prediction.system_probability if latest_prediction else current_market_probability)
    prediction_drift = prediction_probability - entry_probability
    edge = _to_decimal(latest_prediction.edge if latest_prediction else '0')
    confidence = _to_decimal(latest_prediction.confidence if latest_prediction else '0.5')
    narrative_drift = _to_decimal(research_candidate.divergence_score if research_candidate else '0')

    runtime_mode = get_runtime_state().current_mode
    safety = get_safety_status()

    snapshot = {
        'position_id': position.id,
        'market_id': position.market_id,
        'market_title': position.market.title,
        'entry_probability': str(entry_probability),
        'current_market_probability': str(current_market_probability),
        'prediction_probability': str(prediction_probability),
        'prediction_drift': str(prediction_drift),
        'current_edge_estimate': str(edge),
        'confidence': str(confidence),
        'narrative_drift': str(narrative_drift),
        'pnl_realized': str(position.realized_pnl),
        'pnl_unrealized': str(position.unrealized_pnl),
        'runtime_mode': runtime_mode,
        'safety_state': safety.get('status'),
        'watch_severity': latest_watch_event.severity if latest_watch_event else 'info',
        'latest_watch_event_type': latest_watch_event.event_type if latest_watch_event else 'monitor',
        'provider_stale': bool((timezone.now() - position.market.updated_at).total_seconds() > 1800),
    }
    return snapshot, latest_prediction, latest_watch_event
