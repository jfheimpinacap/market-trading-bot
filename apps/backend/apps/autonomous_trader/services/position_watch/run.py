from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.autonomous_trader.models import (
    AutonomousPositionActionDecisionType,
    AutonomousPositionActionExecutionStatus,
    AutonomousPositionActionExecutionType,
    AutonomousPositionWatchRun,
)
from apps.autonomous_trader.services.position_watch.action_decision import decide_action
from apps.autonomous_trader.services.position_watch.action_execution import execute_action
from apps.autonomous_trader.services.position_watch.assessment import assess_candidate
from apps.autonomous_trader.services.position_watch.recommendation import emit_recommendation
from apps.autonomous_trader.services.position_watch.watch_candidates import build_watch_candidates


@transaction.atomic
def run_position_watch(*, actor: str = 'operator-ui', limit: int = 50) -> dict:
    run = AutonomousPositionWatchRun.objects.create(metadata={'actor': actor, 'paper_only': True})
    candidates = build_watch_candidates(watch_run=run)[:limit]

    decisions = []
    executions = []
    recommendations = []
    for candidate in candidates:
        assessment = assess_candidate(candidate)
        decision = decide_action(candidate=candidate, assessment=assessment)
        execution = execute_action(decision=decision)
        recommendation = emit_recommendation(candidate=candidate, decision=decision)
        decisions.append(decision)
        if execution:
            executions.append(execution)
        recommendations.append(recommendation)

    decision_counter = Counter(d.decision_type for d in decisions)
    run.considered_position_count = len(candidates)
    run.hold_count = decision_counter.get(AutonomousPositionActionDecisionType.HOLD_POSITION, 0)
    run.reduce_count = decision_counter.get(AutonomousPositionActionDecisionType.REDUCE_POSITION, 0)
    run.close_count = decision_counter.get(AutonomousPositionActionDecisionType.CLOSE_POSITION, 0)
    run.review_required_count = decision_counter.get(AutonomousPositionActionDecisionType.REVIEW_REQUIRED, 0)
    run.executed_reduce_count = sum(
        1
        for ex in executions
        if ex.execution_type == AutonomousPositionActionExecutionType.REDUCE_EXECUTION
        and ex.execution_status == AutonomousPositionActionExecutionStatus.FILLED
    )
    run.executed_close_count = sum(
        1
        for ex in executions
        if ex.execution_type == AutonomousPositionActionExecutionType.CLOSE_EXECUTION
        and ex.execution_status == AutonomousPositionActionExecutionStatus.FILLED
    )
    run.recommendation_summary = dict(Counter(r.recommendation_type for r in recommendations))
    run.completed_at = timezone.now()
    run.save()

    return {
        'run': run,
        'candidates': candidates,
        'decisions': decisions,
        'executions': executions,
        'recommendations': recommendations,
    }


def build_position_watch_summary() -> dict:
    latest = AutonomousPositionWatchRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'latest_run_id': None,
            'considered_position_count': 0,
            'hold_count': 0,
            'reduce_count': 0,
            'close_count': 0,
            'review_required_count': 0,
            'executed_reduce_count': 0,
            'executed_close_count': 0,
            'recommendation_summary': {},
        }

    return {
        'latest_run_id': latest.id,
        'considered_position_count': latest.considered_position_count,
        'hold_count': latest.hold_count,
        'reduce_count': latest.reduce_count,
        'close_count': latest.close_count,
        'review_required_count': latest.review_required_count,
        'executed_reduce_count': latest.executed_reduce_count,
        'executed_close_count': latest.executed_close_count,
        'recommendation_summary': latest.recommendation_summary,
    }
