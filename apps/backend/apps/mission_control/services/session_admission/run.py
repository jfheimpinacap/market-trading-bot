from __future__ import annotations

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionAdmissionDecision,
    AutonomousSessionAdmissionDecisionStatus,
    AutonomousSessionAdmissionDecisionType,
    AutonomousSessionAdmissionRecommendation,
    AutonomousSessionAdmissionRun,
    AutonomousSessionAdmissionStatus,
)
from apps.mission_control.services.session_admission.admission_apply import apply_admission_decision
from apps.mission_control.services.session_admission.admission_review import evaluate_session_for_admission
from apps.mission_control.services.session_admission.capacity import build_global_capacity_snapshot
from apps.mission_control.services.session_admission.recommendation import emit_admission_recommendation


def _to_decision_type(admission_status: str) -> str:
    mapping = {
        AutonomousSessionAdmissionStatus.ADMIT: AutonomousSessionAdmissionDecisionType.ADMIT_SESSION,
        AutonomousSessionAdmissionStatus.RESUME_ALLOWED: AutonomousSessionAdmissionDecisionType.ALLOW_RESUME,
        AutonomousSessionAdmissionStatus.PARK: AutonomousSessionAdmissionDecisionType.PARK_SESSION,
        AutonomousSessionAdmissionStatus.DEFER: AutonomousSessionAdmissionDecisionType.DEFER_SESSION,
        AutonomousSessionAdmissionStatus.PAUSE: AutonomousSessionAdmissionDecisionType.PAUSE_SESSION,
        AutonomousSessionAdmissionStatus.RETIRE: AutonomousSessionAdmissionDecisionType.RETIRE_SESSION,
        AutonomousSessionAdmissionStatus.MANUAL_REVIEW: AutonomousSessionAdmissionDecisionType.REQUIRE_MANUAL_ADMISSION_REVIEW,
    }
    return mapping[admission_status]


def run_session_admission_review(*, session_ids: list[int] | None = None, auto_apply_safe: bool = True) -> AutonomousSessionAdmissionRun:
    run = AutonomousSessionAdmissionRun.objects.create(started_at=timezone.now(), metadata={'auto_apply_safe': auto_apply_safe})
    capacity_snapshot = build_global_capacity_snapshot(admission_run=run)

    sessions = AutonomousRuntimeSession.objects.filter(
        session_status__in=[
            AutonomousRuntimeSessionStatus.RUNNING,
            AutonomousRuntimeSessionStatus.PAUSED,
            AutonomousRuntimeSessionStatus.DEGRADED,
            AutonomousRuntimeSessionStatus.BLOCKED,
        ]
    ).order_by('-dispatch_count', '-updated_at', '-id')
    if session_ids:
        sessions = sessions.filter(id__in=session_ids)

    counters = {
        'ADMIT': 0,
        'RESUME_ALLOWED': 0,
        'PARK': 0,
        'DEFER': 0,
        'PAUSE': 0,
        'RETIRE': 0,
        'MANUAL_REVIEW': 0,
    }

    running_rank = 0
    for session in sessions[:100]:
        if session.session_status == AutonomousRuntimeSessionStatus.RUNNING:
            running_rank += 1
        review = evaluate_session_for_admission(
            session=session,
            capacity_snapshot=capacity_snapshot,
            admission_run=run,
            running_rank=running_rank,
        )
        counters[review.admission_status] += 1
        decision_type = _to_decision_type(review.admission_status)
        auto_applicable = decision_type in {
            AutonomousSessionAdmissionDecisionType.ADMIT_SESSION,
            AutonomousSessionAdmissionDecisionType.ALLOW_RESUME,
            AutonomousSessionAdmissionDecisionType.PARK_SESSION,
            AutonomousSessionAdmissionDecisionType.DEFER_SESSION,
            AutonomousSessionAdmissionDecisionType.PAUSE_SESSION,
            AutonomousSessionAdmissionDecisionType.RETIRE_SESSION,
        }
        decision = AutonomousSessionAdmissionDecision.objects.create(
            linked_session=session,
            linked_admission_review=review,
            decision_type=decision_type,
            decision_status=AutonomousSessionAdmissionDecisionStatus.PROPOSED,
            auto_applicable=auto_applicable,
            decision_summary=review.review_summary,
            reason_codes=review.reason_codes,
            metadata={'admission_run_id': run.id, 'capacity_snapshot_id': capacity_snapshot.id},
        )
        emit_admission_recommendation(decision=decision)
        if auto_apply_safe and auto_applicable and decision_type in {
            AutonomousSessionAdmissionDecisionType.PARK_SESSION,
            AutonomousSessionAdmissionDecisionType.DEFER_SESSION,
            AutonomousSessionAdmissionDecisionType.PAUSE_SESSION,
            AutonomousSessionAdmissionDecisionType.RETIRE_SESSION,
            AutonomousSessionAdmissionDecisionType.ALLOW_RESUME,
        }:
            apply_admission_decision(decision=decision, automatic=True)

    run.considered_session_count = sum(counters.values())
    run.admitted_count = counters['ADMIT']
    run.resume_allowed_count = counters['RESUME_ALLOWED']
    run.parked_count = counters['PARK']
    run.deferred_count = counters['DEFER']
    run.paused_count = counters['PAUSE']
    run.retired_count = counters['RETIRE']
    run.manual_review_count = counters['MANUAL_REVIEW']
    run.recommendation_summary = (
        f"considered={run.considered_session_count} admit={run.admitted_count} resume={run.resume_allowed_count} "
        f"park={run.parked_count} defer={run.deferred_count} pause={run.paused_count} retire={run.retired_count} manual={run.manual_review_count}"
    )
    run.completed_at = timezone.now()
    run.save(update_fields=[
        'considered_session_count', 'admitted_count', 'resume_allowed_count', 'parked_count', 'deferred_count',
        'paused_count', 'retired_count', 'manual_review_count', 'recommendation_summary', 'completed_at', 'updated_at'
    ])
    return run


def build_session_admission_summary() -> dict:
    latest_run = AutonomousSessionAdmissionRun.objects.order_by('-started_at', '-id').first()
    latest_capacity = latest_run.capacity_snapshots.order_by('-created_at', '-id').first() if latest_run else None
    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'summary': {
            'sessions_considered': latest_run.considered_session_count if latest_run else 0,
            'admitted': latest_run.admitted_count if latest_run else 0,
            'resume_allowed': latest_run.resume_allowed_count if latest_run else 0,
            'parked': latest_run.parked_count if latest_run else 0,
            'deferred': latest_run.deferred_count if latest_run else 0,
            'paused': latest_run.paused_count if latest_run else 0,
            'retired': latest_run.retired_count if latest_run else 0,
            'manual_review': latest_run.manual_review_count if latest_run else 0,
        },
        'latest_capacity_snapshot_id': latest_capacity.id if latest_capacity else None,
        'totals': {
            'runs': AutonomousSessionAdmissionRun.objects.count(),
            'capacity_snapshots': latest_run.capacity_snapshots.count() if latest_run else 0,
            'reviews': latest_run.reviews.count() if latest_run else 0,
            'decisions': AutonomousSessionAdmissionDecision.objects.count(),
            'recommendations': AutonomousSessionAdmissionRecommendation.objects.count(),
        },
    }
