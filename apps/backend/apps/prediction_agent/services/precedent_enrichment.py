from __future__ import annotations

from decimal import Decimal

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import record_agent_precedent_use, run_assist
from apps.memory_retrieval.services.assist import build_prediction_query
from apps.prediction_agent.models import PredictionScore


def apply_prediction_precedents(
    *,
    score: PredictionScore,
    system_probability: Decimal,
    confidence: Decimal,
) -> tuple[Decimal, str, dict]:
    query = build_prediction_query(
        market_title=score.market.title,
        edge=str(score.edge),
        confidence=str(confidence),
    )
    influence = run_assist(
        query_text=query,
        query_type=MemoryQueryType.PREDICTION,
        context_metadata={'market_id': score.market_id, 'source': 'prediction_agent_internal', 'prediction_score_id': score.id},
        limit=6,
    )
    summary = influence.summary
    adjusted_confidence = confidence
    rationale_suffix = 'No strong precedents found for this case.'
    if influence.influence_mode in {'caution_boost', 'confidence_adjust'} and summary.get('matches'):
        adjusted_confidence = max(Decimal('0.0500'), confidence - Decimal('0.0700'))
        rationale_suffix = 'Confidence conservatively adjusted from comparable historical outcomes.'

    precedent_use = record_agent_precedent_use(
        agent_name='prediction_agent',
        source_app='prediction_agent',
        source_object_id=str(score.id),
        influence=influence,
        metadata={'prediction_score_id': score.id},
    )
    context = {
        'precedent_aware': True,
        'badge': 'PRECEDENT_AWARE',
        'influence_mode': influence.influence_mode,
        'precedent_confidence': influence.precedent_confidence,
        'summary': summary,
        'agent_precedent_use_id': precedent_use.id,
    }
    return adjusted_confidence, rationale_suffix, context
