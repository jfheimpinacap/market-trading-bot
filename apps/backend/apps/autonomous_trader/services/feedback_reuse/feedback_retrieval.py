from __future__ import annotations

from dataclasses import dataclass

from apps.autonomous_trader.models import (
    AutonomousFeedbackCandidateContext,
    AutonomousFeedbackRetrievalStatus,
    AutonomousFeedbackReuseRun,
    AutonomousTradeCandidate,
)
from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import run_assist


@dataclass
class CandidateFeedbackContextResult:
    candidate: AutonomousTradeCandidate
    context: AutonomousFeedbackCandidateContext
    influence: object | None


def _build_query(candidate: AutonomousTradeCandidate) -> str:
    return (
        f"Autonomous paper candidate for {candidate.linked_market.title}. "
        f"edge={candidate.adjusted_edge}, confidence={candidate.confidence}, risk_posture={candidate.risk_posture}. "
        "Find similar losses, repeat failure patterns, and reusable conservative lessons."
    )


def build_candidate_contexts(*, reuse_run: AutonomousFeedbackReuseRun, candidates: list[AutonomousTradeCandidate]) -> list[CandidateFeedbackContextResult]:
    results: list[CandidateFeedbackContextResult] = []
    for candidate in candidates:
        context = AutonomousFeedbackCandidateContext.objects.create(
            linked_reuse_run=reuse_run,
            linked_cycle_run=candidate.cycle_run,
            linked_candidate=candidate,
            linked_market=candidate.linked_market,
            retrieval_status=AutonomousFeedbackRetrievalStatus.NO_RETRIEVAL,
            metadata={
                'paper_only': True,
                'authority_boundary': 'memory_context_only',
            },
        )

        try:
            influence = run_assist(
                query_text=_build_query(candidate),
                query_type=MemoryQueryType.RISK,
                context_metadata={
                    'agent': 'autonomous_trader',
                    'candidate_id': candidate.id,
                    'cycle_run_id': candidate.cycle_run_id,
                    'market_id': candidate.linked_market_id,
                },
                limit=6,
                min_similarity=0.58,
            )
            summary = influence.summary or {}
            matches = int(summary.get('matches') or 0)
            failure_modes = (summary.get('prior_failure_modes') or [])[:3]
            lessons = (summary.get('top_lessons') or [])[:3]
            context.retrieval_status = (
                AutonomousFeedbackRetrievalStatus.HITS_FOUND if matches > 0 else AutonomousFeedbackRetrievalStatus.NO_HITS
            )
            context.top_precedent_count = matches
            context.top_failure_modes = failure_modes
            context.top_lessons = lessons
            context.context_summary = (
                'Relevant precedents found for conservative reuse.'
                if matches > 0
                else 'No relevant precedents found for this candidate.'
            )
            context.metadata = {
                **(context.metadata or {}),
                'retrieval_run_id': influence.retrieval_run.id,
                'precedent_confidence': influence.precedent_confidence,
                'suggested_influence_mode': influence.influence_mode,
                'caution_flags': influence.caution_flags,
                'raw_summary': summary,
            }
            context.save(
                update_fields=[
                    'retrieval_status',
                    'top_precedent_count',
                    'top_failure_modes',
                    'top_lessons',
                    'context_summary',
                    'metadata',
                    'updated_at',
                ]
            )
        except Exception as exc:  # conservative fallback if retrieval stack is unavailable
            influence = None
            context.retrieval_status = AutonomousFeedbackRetrievalStatus.BLOCKED
            context.context_summary = 'Retrieval unavailable; candidate kept under conservative no-adjust mode.'
            context.metadata = {
                **(context.metadata or {}),
                'retrieval_error': str(exc),
            }
            context.save(update_fields=['retrieval_status', 'context_summary', 'metadata', 'updated_at'])

        results.append(CandidateFeedbackContextResult(candidate=candidate, context=context, influence=influence))

    return results
