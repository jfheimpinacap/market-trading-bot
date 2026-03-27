from __future__ import annotations

from dataclasses import dataclass

from apps.memory_retrieval.models import (
    AgentPrecedentUse,
    MemoryQueryType,
    MemoryRetrievalRun,
    PrecedentInfluenceMode,
)
from apps.memory_retrieval.services.precedents import build_precedent_summary
from apps.memory_retrieval.services.retrieval import retrieve_precedents


@dataclass
class PrecedentInfluenceSummary:
    retrieval_run: MemoryRetrievalRun
    summary: dict
    influence_mode: str
    precedent_confidence: float
    caution_flags: list[str]


def suggest_influence_mode(*, summary: dict) -> str:
    matches = int(summary.get('matches') or 0)
    caution = len(summary.get('prior_caution_signals') or [])
    avg_similarity = float(summary.get('average_similarity') or 0.0)
    if matches <= 0:
        return PrecedentInfluenceMode.RATIONALE_ONLY
    if caution >= 2 and avg_similarity >= 0.7:
        return PrecedentInfluenceMode.CAUTION_BOOST
    if caution >= 1:
        return PrecedentInfluenceMode.CONFIDENCE_ADJUST
    return PrecedentInfluenceMode.CONTEXT_ONLY


def _precedent_confidence(*, summary: dict) -> float:
    matches = int(summary.get('matches') or 0)
    avg_similarity = float(summary.get('average_similarity') or 0.0)
    density = min(matches / 6, 1.0)
    return round((density * 0.45) + (avg_similarity * 0.55), 4)


def retrieve_with_influence(
    *,
    query_text: str,
    query_type: str = MemoryQueryType.MANUAL,
    context_metadata: dict | None = None,
    limit: int = 6,
    min_similarity: float = 0.58,
) -> PrecedentInfluenceSummary:
    run = retrieve_precedents(
        query_text=query_text,
        query_type=query_type,
        context_metadata=context_metadata or {},
        limit=limit,
        min_similarity=min_similarity,
    )
    summary = build_precedent_summary(run)
    return PrecedentInfluenceSummary(
        retrieval_run=run,
        summary=summary,
        influence_mode=suggest_influence_mode(summary=summary),
        precedent_confidence=_precedent_confidence(summary=summary),
        caution_flags=(summary.get('prior_failure_modes') or [])[:3],
    )


def record_agent_precedent_use(
    *,
    agent_name: str,
    source_app: str,
    source_object_id: str,
    influence: PrecedentInfluenceSummary,
    metadata: dict | None = None,
) -> AgentPrecedentUse:
    return AgentPrecedentUse.objects.create(
        agent_name=agent_name,
        source_app=source_app,
        source_object_id=source_object_id,
        retrieval_run=influence.retrieval_run,
        precedent_count=influence.summary.get('matches') or 0,
        influence_mode=influence.influence_mode,
        metadata={
            'precedent_confidence': influence.precedent_confidence,
            'suggested_influence_mode': influence.influence_mode,
            'caution_flags': influence.caution_flags,
            'summary': influence.summary,
            **(metadata or {}),
        },
    )
