from __future__ import annotations

from decimal import Decimal

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import record_agent_precedent_use, run_assist
from apps.memory_retrieval.services.assist import build_research_query
from apps.research_agent.models import ResearchCandidate


def apply_research_precedents(*, candidate: ResearchCandidate) -> dict:
    query = build_research_query(
        market_title=candidate.market.title,
        thesis=candidate.short_thesis or '',
        relation=candidate.relation,
    )
    influence = run_assist(
        query_text=query,
        query_type=MemoryQueryType.RESEARCH,
        context_metadata={'market_id': candidate.market_id, 'source': 'research_agent_internal'},
        limit=6,
    )
    summary = influence.summary
    caution_count = len(summary.get('prior_caution_signals') or [])
    priority_adjustment = Decimal('0.00')
    if influence.influence_mode in {'caution_boost', 'confidence_adjust'} and caution_count:
        priority_adjustment = Decimal('-3.50')

    precedent_use = record_agent_precedent_use(
        agent_name='research_agent',
        source_app='research_agent',
        source_object_id=str(candidate.id),
        influence=influence,
        metadata={'market_id': candidate.market_id},
    )

    warnings = []
    if caution_count:
        warnings.append('CAUTION_FROM_HISTORY')
    if summary.get('prior_failure_modes'):
        warnings.append('SIMILAR_FAILURE_MODE')
    if summary.get('lessons_learned'):
        warnings.append('LESSON_APPLIED')

    return {
        'precedent_aware': True,
        'badge': 'PRECEDENT_AWARE',
        'influence_mode': influence.influence_mode,
        'precedent_confidence': influence.precedent_confidence,
        'warnings': warnings,
        'summary': summary,
        'agent_precedent_use_id': precedent_use.id,
        'priority_adjustment': float(priority_adjustment),
        'rationale_note': (
            'No strong precedents found for this case.'
            if not summary.get('matches')
            else f"Historical context: {', '.join((summary.get('prior_failure_modes') or [])[:2]) or 'comparable outcomes reviewed'}."
        ),
    }
