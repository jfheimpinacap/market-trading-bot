from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.autonomous_trader.models import AutonomousFeedbackReuseRun, AutonomousTradeCandidate, AutonomousTradeCycleRun
from apps.autonomous_trader.services.feedback_reuse.feedback_retrieval import build_candidate_contexts
from apps.autonomous_trader.services.feedback_reuse.influence import apply_feedback_influence
from apps.autonomous_trader.services.feedback_reuse.recommendation import create_feedback_recommendation
from apps.autonomous_trader.services.feedback_reuse.watch_feedback import build_watch_feedback_patch


def run_feedback_reuse_engine(*, cycle_run: AutonomousTradeCycleRun | None = None, actor: str = 'operator-ui', limit: int = 25) -> AutonomousFeedbackReuseRun:
    reuse_run = AutonomousFeedbackReuseRun.objects.create(metadata={'actor': actor, 'paper_only': True})

    queryset = AutonomousTradeCandidate.objects.select_related('linked_market', 'cycle_run').order_by('-created_at', '-id')
    if cycle_run:
        queryset = queryset.filter(cycle_run=cycle_run)
    candidates = list(queryset[:limit])

    context_results = build_candidate_contexts(reuse_run=reuse_run, candidates=candidates)

    influences = []
    recommendations = []
    for result in context_results:
        influence = apply_feedback_influence(candidate=result.candidate, context=result.context)
        watch_patch = build_watch_feedback_patch(influence=influence)
        influence.metadata = {**(influence.metadata or {}), 'watch_patch': watch_patch}
        influence.save(update_fields=['metadata', 'updated_at'])
        influences.append(influence)
        recommendations.append(create_feedback_recommendation(influence=influence))

    rec_counter = Counter(r.recommendation_type for r in recommendations)
    reuse_run.considered_candidate_count = len(candidates)
    reuse_run.retrieval_attempt_count = len(context_results)
    reuse_run.retrieval_hit_count = sum(1 for r in context_results if r.context.retrieval_status == 'HITS_FOUND')
    reuse_run.influence_applied_count = sum(1 for i in influences if i.influence_status == 'APPLIED')
    reuse_run.watch_caution_count = sum(1 for i in influences if (i.metadata or {}).get('watch_patch', {}).get('watch_priority_up'))
    reuse_run.blocked_or_reduced_count = sum(
        1
        for i in influences
        if i.influence_type in {'BLOCK_REPEAT_PATTERN', 'CONFIDENCE_REDUCTION'} and i.influence_status == 'APPLIED'
    )
    reuse_run.recommendation_summary = dict(rec_counter)
    reuse_run.completed_at = timezone.now()
    reuse_run.metadata = {**(reuse_run.metadata or {}), 'cycle_run_id': cycle_run.id if cycle_run else None}
    reuse_run.save(
        update_fields=[
            'considered_candidate_count',
            'retrieval_attempt_count',
            'retrieval_hit_count',
            'influence_applied_count',
            'watch_caution_count',
            'blocked_or_reduced_count',
            'recommendation_summary',
            'completed_at',
            'metadata',
            'updated_at',
        ]
    )
    return reuse_run


def build_feedback_summary() -> dict:
    latest = AutonomousFeedbackReuseRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'latest_run_id': None,
            'considered_candidate_count': 0,
            'retrieval_hit_count': 0,
            'influence_applied_count': 0,
            'watch_caution_count': 0,
            'blocked_or_reduced_count': 0,
            'no_relevant_learning_found_count': 0,
            'recommendation_summary': {},
        }

    return {
        'latest_run_id': latest.id,
        'considered_candidate_count': latest.considered_candidate_count,
        'retrieval_hit_count': latest.retrieval_hit_count,
        'influence_applied_count': latest.influence_applied_count,
        'watch_caution_count': latest.watch_caution_count,
        'blocked_or_reduced_count': latest.blocked_or_reduced_count,
        'no_relevant_learning_found_count': int((latest.recommendation_summary or {}).get('NO_RELEVANT_LEARNING_FOUND', 0)),
        'recommendation_summary': latest.recommendation_summary,
    }
