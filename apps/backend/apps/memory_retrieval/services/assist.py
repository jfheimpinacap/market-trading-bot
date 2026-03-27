from __future__ import annotations

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services.influence import PrecedentInfluenceSummary, retrieve_with_influence


def build_research_query(*, market_title: str, thesis: str, relation: str) -> str:
    return f'Research narrative for {market_title}. Relation={relation}. Thesis={thesis}. Prior similar outcomes and failure patterns.'


def build_prediction_query(*, market_title: str, edge: str, confidence: str) -> str:
    return (
        f'Prediction setup for {market_title}. Estimated edge={edge}, confidence={confidence}. '
        'Find similar prediction patterns with execution realism outcomes.'
    )


def build_risk_query(*, market_title: str, risk_level: str, risk_score: str) -> str:
    return f'Risk assessment for {market_title}. risk_level={risk_level}, risk_score={risk_score}. Similar adverse outcomes and caution lessons.'


def build_signal_query(*, market_title: str, opportunity_score: str, risk_level: str) -> str:
    return f'Signal fusion candidate {market_title}. opportunity_score={opportunity_score}, risk_level={risk_level}. Similar watch vs proposal outcomes.'


def build_postmortem_query(*, market_title: str, outcome: str) -> str:
    return f'Postmortem review for {market_title}. outcome={outcome}. Similar prior failures and applicable lessons learned.'


def run_assist(
    *,
    query_text: str,
    query_type: str,
    context_metadata: dict | None = None,
    limit: int = 6,
    min_similarity: float = 0.58,
) -> PrecedentInfluenceSummary:
    return retrieve_with_influence(
        query_text=query_text,
        query_type=query_type or MemoryQueryType.MANUAL,
        context_metadata=context_metadata or {},
        limit=limit,
        min_similarity=min_similarity,
    )
