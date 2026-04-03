from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.governance_backlog_pressure.services.backlog_pressure import assess_backlog_pressure
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
        assessment = assess_backlog_pressure()
        snapshot = GovernanceBacklogPressureSnapshot.objects.create(
            linked_backlog_pressure_run=run,
            open_item_count=assessment.open_item_count,
            overdue_count=assessment.overdue_count,
            overdue_p1_count=assessment.overdue_p1_count,
            stale_blocked_count=assessment.stale_blocked_count,
            persistent_stale_blocked_count=assessment.persistent_stale_blocked_count,
            pressure_score=assessment.pressure_score,
            governance_backlog_pressure_state=assessment.governance_backlog_pressure_state,
            snapshot_summary=assessment.snapshot_summary,
            reason_codes=assessment.reason_codes,
            metadata=assessment.metadata,
        )

        decision_payload = build_backlog_pressure_decision(snapshot=snapshot)
        decision = GovernanceBacklogPressureDecision.objects.create(
            linked_backlog_pressure_snapshot=snapshot,
            linked_backlog_pressure_run=run,
            decision_type=decision_payload.decision_type,
            decision_summary=decision_payload.decision_summary,
            reason_codes=decision_payload.reason_codes,
            metadata=decision_payload.metadata,
        )

        recommendation_payload = build_backlog_pressure_recommendation(decision=decision)
        GovernanceBacklogPressureRecommendation.objects.create(
            linked_backlog_pressure_decision=decision,
            linked_backlog_pressure_snapshot=snapshot,
            recommendation_type=recommendation_payload.recommendation_type,
            rationale=recommendation_payload.rationale,
            confidence=recommendation_payload.confidence,
            blockers=recommendation_payload.blockers,
        )

        run.considered_item_count = assessment.open_item_count
        run.pressure_state = assessment.governance_backlog_pressure_state
        run.completed_at = timezone.now()
        run.metadata = {
            'overdue_count': assessment.overdue_count,
            'overdue_p1_count': assessment.overdue_p1_count,
            'stale_blocked_count': assessment.stale_blocked_count,
            'persistent_stale_blocked_count': assessment.persistent_stale_blocked_count,
            'pressure_score': assessment.pressure_score,
        }
        run.save(update_fields=['considered_item_count', 'pressure_state', 'completed_at', 'metadata', 'updated_at'])

    return run


def governance_backlog_pressure_summary() -> dict:
    latest_run = GovernanceBacklogPressureRun.objects.order_by('-started_at', '-id').first()
    latest_snapshot = GovernanceBacklogPressureSnapshot.objects.order_by('-created_at', '-id').first()
    latest_decision = GovernanceBacklogPressureDecision.objects.order_by('-created_at', '-id').first()

    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'governance_backlog_pressure_state': (
            latest_snapshot.governance_backlog_pressure_state
            if latest_snapshot
            else 'NORMAL'
        ),
        'latest_counts': {
            'considered': latest_run.considered_item_count if latest_run else 0,
            'open_items': latest_snapshot.open_item_count if latest_snapshot else 0,
            'overdue': latest_snapshot.overdue_count if latest_snapshot else 0,
            'overdue_p1': latest_snapshot.overdue_p1_count if latest_snapshot else 0,
            'stale_blocked': latest_snapshot.stale_blocked_count if latest_snapshot else 0,
            'persistent_stale_blocked': latest_snapshot.persistent_stale_blocked_count if latest_snapshot else 0,
        },
        'totals': {
            'runs': GovernanceBacklogPressureRun.objects.count(),
            'snapshots': GovernanceBacklogPressureSnapshot.objects.count(),
            'decisions': GovernanceBacklogPressureDecision.objects.count(),
            'recommendations': GovernanceBacklogPressureRecommendation.objects.count(),
        },
        'latest_decision': {
            'id': latest_decision.id if latest_decision else None,
            'decision_type': latest_decision.decision_type if latest_decision else None,
        },
    }
