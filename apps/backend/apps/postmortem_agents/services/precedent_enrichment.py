from __future__ import annotations

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import record_agent_precedent_use, run_assist
from apps.memory_retrieval.services.assist import build_postmortem_query
from apps.postmortem_agents.models import PostmortemBoardRun


def build_postmortem_precedent_context(*, board_run: PostmortemBoardRun) -> dict:
    review = board_run.related_trade_review
    query = build_postmortem_query(
        market_title=review.market.title if review.market_id else f'trade-{review.id}',
        outcome=review.outcome,
    )
    influence = run_assist(
        query_text=query,
        query_type=MemoryQueryType.POSTMORTEM,
        context_metadata={'review_id': review.id, 'board_run_id': board_run.id, 'source': 'postmortem_board_internal'},
        limit=8,
    )
    precedent_use = record_agent_precedent_use(
        agent_name='postmortem_board',
        source_app='postmortem_agents',
        source_object_id=str(board_run.id),
        influence=influence,
        metadata={'trade_review_id': review.id},
    )
    return {
        'precedent_aware': True,
        'badge': 'PRECEDENT_AWARE',
        'influence_mode': influence.influence_mode,
        'precedent_confidence': influence.precedent_confidence,
        'summary': influence.summary,
        'agent_precedent_use_id': precedent_use.id,
        'similar_prior_failures': influence.summary.get('prior_failure_modes') or [],
        'rationale_note': 'No strong precedents found for this case.' if not influence.summary.get('matches') else 'Similar prior failures included in board context.',
    }
