from __future__ import annotations

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousSessionHealthRun,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionHealthStatus,
    AutonomousSessionInterventionDecision,
    AutonomousSessionInterventionDecisionType,
    AutonomousSessionInterventionRecord,
    AutonomousSessionHealthRecommendation,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
)
from apps.mission_control.services.session_health.anomaly import detect_anomalies
from apps.mission_control.services.session_health.health_snapshot import build_health_snapshot
from apps.mission_control.services.session_health.intervention import apply_intervention, decide_intervention
from apps.mission_control.services.session_health.recommendation import emit_health_recommendation


def run_session_health_review(*, session_ids: list[int] | None = None, auto_apply_safe: bool = True) -> AutonomousSessionHealthRun:
    run = AutonomousSessionHealthRun.objects.create()
    sessions = AutonomousRuntimeSession.objects.filter(
        session_status__in=[
            AutonomousRuntimeSessionStatus.RUNNING,
            AutonomousRuntimeSessionStatus.PAUSED,
            AutonomousRuntimeSessionStatus.BLOCKED,
        ]
    ).order_by('-updated_at', '-id')
    if session_ids:
        sessions = sessions.filter(id__in=session_ids)

    considered = 0
    healthy = 0
    anomaly_count = 0
    pause_recommended = 0
    stop_recommended = 0
    resume_recommended = 0
    manual_review = 0
    applied = 0

    for session in sessions[:80]:
        considered += 1
        snapshot_result = build_health_snapshot(session=session, health_run=run)
        if snapshot_result.snapshot.session_health_status == AutonomousSessionHealthStatus.HEALTHY:
            healthy += 1
        anomalies = detect_anomalies(snapshot=snapshot_result.snapshot)
        anomaly_count += len(anomalies)
        decision = decide_intervention(snapshot=snapshot_result.snapshot, anomalies=anomalies)

        if decision.decision_type == AutonomousSessionInterventionDecisionType.PAUSE_SESSION:
            pause_recommended += 1
        elif decision.decision_type == AutonomousSessionInterventionDecisionType.STOP_SESSION:
            stop_recommended += 1
        elif decision.decision_type == AutonomousSessionInterventionDecisionType.RESUME_SESSION:
            resume_recommended += 1
        elif decision.decision_type in {
            AutonomousSessionInterventionDecisionType.REQUIRE_MANUAL_REVIEW,
            AutonomousSessionInterventionDecisionType.ESCALATE_TO_INCIDENT_REVIEW,
        }:
            manual_review += 1

        record = apply_intervention(decision=decision, automatic=auto_apply_safe) if auto_apply_safe else None
        if record and record.intervention_status == 'APPLIED':
            applied += 1

        emit_health_recommendation(decision=decision)

    run.considered_session_count = considered
    run.healthy_count = healthy
    run.anomaly_count = anomaly_count
    run.pause_recommended_count = pause_recommended
    run.stop_recommended_count = stop_recommended
    run.resume_recommended_count = resume_recommended
    run.manual_review_count = manual_review
    run.intervention_applied_count = applied
    run.recommendation_summary = (
        f'health-reviewed={considered} healthy={healthy} anomalies={anomaly_count} '
        f'pause={pause_recommended} stop={stop_recommended} resume={resume_recommended} '
        f'manual/escalation={manual_review}'
    )
    run.completed_at = timezone.now()
    run.metadata = {'auto_apply_safe': auto_apply_safe}
    run.save(
        update_fields=[
            'considered_session_count',
            'healthy_count',
            'anomaly_count',
            'pause_recommended_count',
            'stop_recommended_count',
            'resume_recommended_count',
            'manual_review_count',
            'intervention_applied_count',
            'recommendation_summary',
            'completed_at',
            'metadata',
            'updated_at',
        ]
    )
    return run


def build_session_health_summary() -> dict:
    latest_run = AutonomousSessionHealthRun.objects.order_by('-started_at', '-id').first()
    latest_snapshot = AutonomousRuntimeSession.objects.order_by('-updated_at', '-id').first()

    decisions = AutonomousSessionInterventionDecision.objects.order_by('-created_at', '-id')[:300]
    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'summary': {
            'sessions_reviewed': latest_run.considered_session_count if latest_run else 0,
            'healthy': latest_run.healthy_count if latest_run else 0,
            'anomalies': latest_run.anomaly_count if latest_run else 0,
            'pause_recommended': latest_run.pause_recommended_count if latest_run else 0,
            'stop_recommended': latest_run.stop_recommended_count if latest_run else 0,
            'resume_recommended': latest_run.resume_recommended_count if latest_run else 0,
            'manual_review_or_escalation': latest_run.manual_review_count if latest_run else 0,
            'interventions_applied': latest_run.intervention_applied_count if latest_run else 0,
        },
        'totals': {
            'health_runs': AutonomousSessionHealthRun.objects.count(),
            'snapshots': AutonomousSessionHealthSnapshot.objects.count(),
            'decisions': AutonomousSessionInterventionDecision.objects.count(),
            'records': AutonomousSessionInterventionRecord.objects.count(),
            'recommendations': AutonomousSessionHealthRecommendation.objects.count(),
        },
        'latest_session_id': latest_snapshot.id if latest_snapshot else None,
        'decision_breakdown': {
            'keep_running': sum(1 for decision in decisions if decision.decision_type == AutonomousSessionInterventionDecisionType.KEEP_RUNNING),
            'pause': sum(1 for decision in decisions if decision.decision_type == AutonomousSessionInterventionDecisionType.PAUSE_SESSION),
            'resume': sum(1 for decision in decisions if decision.decision_type == AutonomousSessionInterventionDecisionType.RESUME_SESSION),
            'stop': sum(1 for decision in decisions if decision.decision_type == AutonomousSessionInterventionDecisionType.STOP_SESSION),
            'manual': sum(1 for decision in decisions if decision.decision_type == AutonomousSessionInterventionDecisionType.REQUIRE_MANUAL_REVIEW),
            'escalate': sum(1 for decision in decisions if decision.decision_type == AutonomousSessionInterventionDecisionType.ESCALATE_TO_INCIDENT_REVIEW),
        },
    }
