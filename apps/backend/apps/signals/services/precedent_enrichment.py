from __future__ import annotations

from decimal import Decimal

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import record_agent_precedent_use, run_assist
from apps.memory_retrieval.services.assist import build_signal_query
from apps.signals.models import OpportunityStatus


def apply_signal_precedents(
    *,
    opportunity_id: int,
    market_id: int,
    market_title: str,
    opportunity_score: Decimal,
    risk_level: str,
) -> dict:
    query = build_signal_query(
        market_title=market_title,
        opportunity_score=str(opportunity_score),
        risk_level=risk_level,
    )
    influence = run_assist(
        query_text=query,
        query_type=MemoryQueryType.RISK,
        context_metadata={'market_id': market_id, 'opportunity_signal_id': opportunity_id, 'source': 'signal_fusion_internal'},
        limit=5,
    )
    summary = influence.summary
    score_adjustment = Decimal('-6.00') if influence.influence_mode in {'caution_boost', 'confidence_adjust'} and summary.get('matches') else Decimal('0.00')
    status_override = OpportunityStatus.WATCH if score_adjustment and len(summary.get('prior_caution_signals') or []) else None
    precedent_use = record_agent_precedent_use(
        agent_name='signal_fusion_agent',
        source_app='signals',
        source_object_id=str(opportunity_id),
        influence=influence,
        metadata={'opportunity_signal_id': opportunity_id},
    )
    return {
        'precedent_aware': True,
        'badge': 'PRECEDENT_AWARE',
        'influence_mode': influence.influence_mode,
        'precedent_confidence': influence.precedent_confidence,
        'summary': summary,
        'agent_precedent_use_id': precedent_use.id,
        'score_adjustment': str(score_adjustment),
        'status_override': status_override,
        'rationale_note': 'No strong precedents found for this case.' if not summary.get('matches') else 'CAUTION_FROM_HISTORY',
    }
