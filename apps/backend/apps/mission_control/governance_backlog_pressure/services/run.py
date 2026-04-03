from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.governance_backlog_pressure.services.backlog_pressure import build_backlog_pressure_snapshot
from apps.mission_control.governance_backlog_pressure.services.decision import build_backlog_pressure_decision
from apps.mission_control.governance_backlog_pressure.services.recommendation import build_backlog_pressure_recommendation
from apps.mission_control.models import (
    GovernanceBacklogPressureDecision,
    GovernanceBacklogPressureRecommendation,
    GovernanceBacklogPressureRun,
    GovernanceBacklogPressureSnapshot,
)


def run_governance_backlog_pressure_review() -> GovernanceBacklogPressureRun:
    run = GovernanceBacklogPressureRun.objects.create(started_at=timezone.now())

    with transaction.atomic():
        snapshot = build_backlog_pressure_snapshot(pressure_run=run)
        decision = build_backlog_pressure_decision(snapshot)
        recommendation = build_backlog_pressure_recommendation(snapshot=snapshot, decision=decision)

        run.considered_item_count = snapshot.open_item_count + snapshot.in_review_count
        run.high_priority_item_count = snapshot.p1_count + snapshot.p2_count
        run.overdue_item_count = snapshot.overdue_count
        run.blocked_stale_count = snapshot.stale_blocked_count
        run.followup_due_count = snapshot.followup_due_count
        run.metadata = {
            'snapshot_id': snapshot.id,
            'decision_id': decision.id,
            'recommendation_id': recommendation.id,
            'pressure_state': snapshot.pressure_state,
        }
        run.completed_at = timezone.now()
        run.save()

    return run


def governance_backlog_pressure_summary() -> dict:
    latest_run = GovernanceBacklogPressureRun.objects.order_by('-started_at', '-id').first()
    latest_snapshot = GovernanceBacklogPressureSnapshot.objects.order_by('-created_at', '-id').first()
    latest_decision = GovernanceBacklogPressureDecision.objects.order_by('-created_at', '-id').first()
    latest_recommendation = GovernanceBacklogPressureRecommendation.objects.order_by('-created_at', '-id').first()

    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'governance_backlog_pressure_state': latest_snapshot.pressure_state if latest_snapshot else 'NORMAL',
        'latest_snapshot_id': latest_snapshot.id if latest_snapshot else None,
        'latest_decision_id': latest_decision.id if latest_decision else None,
        'latest_recommendation_id': latest_recommendation.id if latest_recommendation else None,
        'totals': {
            'runs': GovernanceBacklogPressureRun.objects.count(),
            'snapshots': GovernanceBacklogPressureSnapshot.objects.count(),
            'decisions': GovernanceBacklogPressureDecision.objects.count(),
            'recommendations': GovernanceBacklogPressureRecommendation.objects.count(),
        },
        'latest_counts': {
            'considered_item_count': latest_run.considered_item_count if latest_run else 0,
            'high_priority_item_count': latest_run.high_priority_item_count if latest_run else 0,
            'overdue_item_count': latest_run.overdue_item_count if latest_run else 0,
            'blocked_stale_count': latest_run.blocked_stale_count if latest_run else 0,
            'followup_due_count': latest_run.followup_due_count if latest_run else 0,
        },
    }
