from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.paper_trading.models import PaperPosition
from apps.risk_agent.models import (
    AutonomousExecutionReadiness,
    RiskIntakeRecommendation,
    RiskRuntimeApprovalStatus,
    RiskRuntimeRun,
)
from apps.risk_agent.services.approval import build_approval_decision
from apps.risk_agent.services.execution_readiness import build_execution_readiness
from apps.risk_agent.services.intake import build_runtime_candidates
from apps.risk_agent.services.recommendation import build_runtime_recommendations
from apps.risk_agent.services.sizing_runtime import build_sizing_plan
from apps.risk_agent.services.watch_plan import build_watch_plan


def _is_reduce_or_exit_candidate(*, candidate, approval_status: str) -> bool:
    if approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
        return True
    token_blob = ' '.join(
        [str(getattr(candidate, 'context_summary', '') or '')]
        + [str(code or '') for code in list(getattr(candidate, 'reason_codes', []) or [])]
    ).upper()
    return any(token in token_blob for token in {'EXIT', 'CLOSE', 'CLOSING', 'REDUCE', 'DE-RISK', 'DERISK', 'TRIM'})


def _should_throttle_readiness_for_valid_active_exposure(
    *,
    candidate,
    approval_status: str,
    traced_markets: set[int],
    active_position_market_ids: set[int],
) -> bool:
    market_id = int(getattr(candidate, 'linked_market_id', 0) or 0)
    if market_id <= 0:
        return False
    if market_id not in active_position_market_ids:
        return False
    if _is_reduce_or_exit_candidate(candidate=candidate, approval_status=approval_status):
        return False
    return market_id in traced_markets


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
    needs_review_count = 0
    watch_required_count = 0
    execution_ready_count = 0
    traced_valid_active_exposure_markets: set[int] = set()
    first_readiness_by_market_id: dict[int, AutonomousExecutionReadiness] = {}
    active_position_market_ids: set[int] = {
        int(market_id)
        for market_id in PaperPosition.objects.filter(status='OPEN', quantity__gt=0).values_list('market_id', flat=True)
        if market_id is not None
    }

    for candidate in build_result.candidates:
        approval = build_approval_decision(candidate=candidate)
        sizing = build_sizing_plan(candidate=candidate, approval_decision=approval)
        watch_plan = build_watch_plan(candidate=candidate, sizing_plan=sizing, approval_decision=approval)
        market_id = int(getattr(candidate, 'linked_market_id', 0) or 0)
        throttle_readiness = _should_throttle_readiness_for_valid_active_exposure(
            candidate=candidate,
            approval_status=approval.approval_status,
            traced_markets=traced_valid_active_exposure_markets,
            active_position_market_ids=active_position_market_ids,
        )
        if throttle_readiness and market_id in first_readiness_by_market_id:
            readiness = first_readiness_by_market_id[market_id]
        else:
            readiness = build_execution_readiness(approval_decision=approval, sizing_plan=sizing, watch_plan=watch_plan)
            if market_id in active_position_market_ids and not _is_reduce_or_exit_candidate(
                candidate=candidate,
                approval_status=approval.approval_status,
            ):
                traced_valid_active_exposure_markets.add(market_id)
                first_readiness_by_market_id.setdefault(market_id, readiness)
        recommendations = build_runtime_recommendations(
            runtime_run=runtime_run,
            candidate=candidate,
            approval_decision=approval,
            watch_plan=watch_plan,
            readiness=readiness,
        )

        if approval.approval_status == RiskRuntimeApprovalStatus.APPROVED:
            approved_count += 1
        elif approval.approval_status == RiskRuntimeApprovalStatus.BLOCKED:
            blocked_count += 1
        elif approval.approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
            approved_count += 1
            reduced_count += 1
        elif approval.approval_status == RiskRuntimeApprovalStatus.NEEDS_REVIEW:
            needs_review_count += 1

        if approval.watch_required:
            watch_required_count += 1

        if readiness.readiness_status in {'READY', 'READY_REDUCED'}:
            execution_ready_count += 1

    recommendation_counts = Counter(
        RiskIntakeRecommendation.objects.filter(runtime_run=runtime_run).values_list('recommendation_type', flat=True)
    )

    runtime_run.candidate_count = len(build_result.candidates)
    runtime_run.considered_handoff_count = build_result.considered_count
    runtime_run.approved_count = approved_count
    runtime_run.blocked_count = blocked_count
    runtime_run.reduced_size_count = reduced_count
    runtime_run.needs_review_count = needs_review_count
    runtime_run.watch_required_count = watch_required_count
    runtime_run.execution_ready_count = execution_ready_count
    runtime_run.sent_to_execution_sim_count = execution_ready_count
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
            'considered_handoff_count',
            'approved_count',
            'blocked_count',
            'reduced_size_count',
            'needs_review_count',
            'watch_required_count',
            'execution_ready_count',
            'sent_to_execution_sim_count',
            'recommendation_summary',
            'completed_at',
            'metadata',
            'updated_at',
        ]
    )
    return runtime_run
