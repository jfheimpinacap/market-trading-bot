from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.autonomous_trader.models import AutonomousExecutionDecisionType, AutonomousExecutionIntakeRun, AutonomousTradeCycleRun
from apps.autonomous_trader.services.execution_intake.decision import decide_intake_candidate
from apps.autonomous_trader.services.execution_intake.dispatch import dispatch_execution_decision
from apps.autonomous_trader.services.execution_intake.intake import build_intake_candidates
from apps.autonomous_trader.services.execution_intake.recommendation import create_recommendation


@transaction.atomic
def run_execution_intake(*, actor: str = 'operator-ui', limit: int = 25):
    cycle_run = AutonomousTradeCycleRun.objects.create(cycle_mode='FULL_AUTONOMOUS_PAPER_LOOP', metadata={'source': 'execution_intake', 'actor': actor})
    run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), linked_cycle_run=cycle_run, metadata={'actor': actor})
    intake = build_intake_candidates(run=run, limit=limit)

    decisions = []
    dispatches = []
    recommendations = []
    for candidate in intake.candidates:
        decision = decide_intake_candidate(candidate=candidate)
        dispatch = dispatch_execution_decision(decision=decision)
        recommendation = create_recommendation(decision=decision, dispatch_record=dispatch)
        decisions.append(decision)
        dispatches.append(dispatch)
        recommendations.append(recommendation)

    decision_counter = Counter(d.decision_type for d in decisions)
    run.considered_readiness_count = len(intake.candidates)
    run.execute_now_count = decision_counter.get(AutonomousExecutionDecisionType.EXECUTE_NOW, 0)
    run.execute_reduced_count = decision_counter.get(AutonomousExecutionDecisionType.EXECUTE_REDUCED, 0)
    run.watch_count = decision_counter.get(AutonomousExecutionDecisionType.KEEP_ON_WATCH, 0)
    run.defer_count = decision_counter.get(AutonomousExecutionDecisionType.DEFER, 0)
    run.blocked_count = decision_counter.get(AutonomousExecutionDecisionType.BLOCK, 0)
    run.manual_review_count = decision_counter.get(AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW, 0)
    run.dispatch_count = sum(1 for d in dispatches if d.dispatch_status in {'DISPATCHED', 'FILLED', 'PARTIAL'})
    run.recommendation_summary = dict(Counter(r.recommendation_type for r in recommendations))
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            'considered_readiness_count',
            'execute_now_count',
            'execute_reduced_count',
            'watch_count',
            'defer_count',
            'blocked_count',
            'manual_review_count',
            'dispatch_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )

    return {
        'run': run,
        'intake_candidates': intake.candidates,
        'decisions': decisions,
        'dispatches': dispatches,
        'recommendations': recommendations,
    }


def build_execution_intake_summary() -> dict:
    latest = AutonomousExecutionIntakeRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'latest_run_id': None,
            'considered_readiness_count': 0,
            'execute_now_count': 0,
            'execute_reduced_count': 0,
            'watch_count': 0,
            'defer_count': 0,
            'blocked_count': 0,
            'manual_review_count': 0,
            'dispatch_count': 0,
            'recommendation_summary': {},
        }

    return {
        'latest_run_id': latest.id,
        'considered_readiness_count': latest.considered_readiness_count,
        'execute_now_count': latest.execute_now_count,
        'execute_reduced_count': latest.execute_reduced_count,
        'watch_count': latest.watch_count,
        'defer_count': latest.defer_count,
        'blocked_count': latest.blocked_count,
        'manual_review_count': latest.manual_review_count,
        'dispatch_count': latest.dispatch_count,
        'recommendation_summary': latest.recommendation_summary,
    }
