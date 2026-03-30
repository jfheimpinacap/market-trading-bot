from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.risk_agent.models import RiskRuntimeApprovalStatus, RiskRuntimeRecommendation, RiskRuntimeRun
from apps.risk_agent.services.approval import build_approval_decision
from apps.risk_agent.services.candidate_building import build_runtime_candidates
from apps.risk_agent.services.recommendation import build_runtime_recommendations
from apps.risk_agent.services.sizing_runtime import build_sizing_plan
from apps.risk_agent.services.watch_plan import build_watch_plan


def run_risk_runtime_review(*, triggered_by: str = 'manual') -> RiskRuntimeRun:
    runtime_run = RiskRuntimeRun.objects.create(
        started_at=timezone.now(),
        metadata={
            'triggered_by': triggered_by,
            'paper_demo_only': True,
            'manual_first': True,
            'execution_authority': 'recommendation_only',
        },
    )

    build_result = build_runtime_candidates(runtime_run=runtime_run)
    approved_count = 0
    blocked_count = 0
    reduced_count = 0
    watch_required_count = 0
    sent_to_execution_sim_count = 0

    for candidate in build_result.candidates:
        approval = build_approval_decision(candidate=candidate)
        sizing = build_sizing_plan(candidate=candidate, approval_decision=approval)
        watch_plan = build_watch_plan(candidate=candidate, sizing_plan=sizing, approval_decision=approval)
        recommendations = build_runtime_recommendations(
            runtime_run=runtime_run,
            candidate=candidate,
            approval_decision=approval,
            watch_plan=watch_plan,
        )

        if approval.approval_status == RiskRuntimeApprovalStatus.APPROVED:
            approved_count += 1
        elif approval.approval_status == RiskRuntimeApprovalStatus.BLOCKED:
            blocked_count += 1
        elif approval.approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
            approved_count += 1
            reduced_count += 1

        if approval.watch_required:
            watch_required_count += 1

        if any(rec.recommendation_type == 'SEND_TO_EXECUTION_SIMULATOR' for rec in recommendations):
            sent_to_execution_sim_count += 1

    recommendation_counts = Counter(
        RiskRuntimeRecommendation.objects.filter(runtime_run=runtime_run).values_list('recommendation_type', flat=True)
    )

    runtime_run.candidate_count = len(build_result.candidates)
    runtime_run.approved_count = approved_count
    runtime_run.blocked_count = blocked_count
    runtime_run.reduced_size_count = reduced_count
    runtime_run.watch_required_count = watch_required_count
    runtime_run.sent_to_execution_sim_count = sent_to_execution_sim_count
    runtime_run.recommendation_summary = dict(recommendation_counts)
    runtime_run.completed_at = timezone.now()
    runtime_run.metadata = {
        **(runtime_run.metadata or {}),
        'skipped_candidates': build_result.skipped_count,
        'portfolio_governor_context': {'risk_budget': 'conservative'},
        'position_manager_context': {'watch_board_enabled': True},
    }
    runtime_run.save(
        update_fields=[
            'candidate_count',
            'approved_count',
            'blocked_count',
            'reduced_size_count',
            'watch_required_count',
            'sent_to_execution_sim_count',
            'recommendation_summary',
            'completed_at',
            'metadata',
            'updated_at',
        ]
    )
    return runtime_run
