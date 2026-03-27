from __future__ import annotations

from decimal import Decimal

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import record_agent_precedent_use, run_assist
from apps.memory_retrieval.services.assist import build_risk_query
from apps.risk_agent.models import RiskAssessment


def apply_risk_precedents(*, assessment: RiskAssessment) -> dict:
    market_title = assessment.market.title if assessment.market else 'unknown market'
    query = build_risk_query(
        market_title=market_title,
        risk_level=assessment.risk_level,
        risk_score=str(assessment.risk_score or '0'),
    )
    influence = run_assist(
        query_text=query,
        query_type=MemoryQueryType.RISK,
        context_metadata={'market_id': assessment.market_id, 'assessment_id': assessment.id, 'source': 'risk_agent_internal'},
        limit=6,
    )
    summary = influence.summary
    caution_hit = influence.influence_mode == 'caution_boost' and bool(summary.get('matches'))
    score_adjustment = Decimal('-6.00') if caution_hit else Decimal('0.00')
    review_required = caution_hit and len(summary.get('prior_caution_signals') or []) >= 1

    precedent_use = record_agent_precedent_use(
        agent_name='risk_agent',
        source_app='risk_agent',
        source_object_id=str(assessment.id),
        influence=influence,
        metadata={'assessment_id': assessment.id},
    )
    return {
        'precedent_aware': True,
        'badge': 'PRECEDENT_AWARE',
        'influence_mode': influence.influence_mode,
        'precedent_confidence': influence.precedent_confidence,
        'summary': summary,
        'agent_precedent_use_id': precedent_use.id,
        'caution_from_history': caution_hit,
        'review_required': review_required,
        'risk_score_adjustment': str(score_adjustment),
        'rationale_note': 'No strong precedents found for this case.' if not summary.get('matches') else 'Historical adverse cases suggest extra caution.',
    }
