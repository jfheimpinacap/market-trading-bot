from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.opportunity_supervisor.models import OpportunityCycleRuntimeRun
from apps.opportunity_supervisor.services.candidate_building import build_fusion_candidates
from apps.opportunity_supervisor.services.fusion import assess_candidate
from apps.opportunity_supervisor.services.proposal_handoff import create_paper_proposal
from apps.opportunity_supervisor.services.recommendation import create_recommendations


@transaction.atomic
def run_opportunity_cycle_review(*, triggered_by: str = 'manual_api') -> OpportunityCycleRuntimeRun:
    runtime_run = OpportunityCycleRuntimeRun.objects.create(
        started_at=timezone.now(),
        metadata={
            'triggered_by': triggered_by,
            'paper_only': True,
            'manual_first': True,
            'auto_trading_enabled': False,
            'real_execution_enabled': False,
        },
    )

    candidates = build_fusion_candidates(runtime_run=runtime_run)
    assessments = [assess_candidate(candidate=candidate) for candidate in candidates]
    proposals = [create_paper_proposal(assessment=assessment) for assessment in assessments]

    recommendation_counter = Counter()
    total_recommendations = 0
    for assessment, proposal in zip(assessments, proposals):
        recommendations = create_recommendations(assessment=assessment, proposal=proposal)
        total_recommendations += len(recommendations)
        recommendation_counter.update(item.recommendation_type for item in recommendations)

    runtime_run.completed_at = timezone.now()
    runtime_run.candidate_count = len(candidates)
    runtime_run.fused_count = len(assessments)
    runtime_run.ready_for_proposal_count = sum(1 for item in assessments if item.fusion_status == 'READY_FOR_PROPOSAL')
    runtime_run.watch_count = sum(1 for item in assessments if item.fusion_status == 'WATCH_ONLY')
    runtime_run.blocked_count = sum(1 for item in assessments if item.fusion_status in {'BLOCKED_BY_RISK', 'BLOCKED_BY_LEARNING'})
    runtime_run.sent_to_proposal_count = sum(1 for item in proposals if item.proposal_id)
    runtime_run.sent_to_execution_sim_context_count = sum(1 for item in proposals if item.execution_sim_recommended)
    runtime_run.recommendation_summary = {
        'total_recommendations': total_recommendations,
        'by_type': dict(recommendation_counter),
    }
    runtime_run.save()
    return runtime_run
