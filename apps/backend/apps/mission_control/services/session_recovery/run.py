from __future__ import annotations

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousResumeDecision,
    AutonomousResumeDecisionType,
    AutonomousResumeRecord,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionRecoveryRecommendation,
    AutonomousSessionRecoveryRun,
    AutonomousSessionRecoverySnapshot,
    AutonomousRecoveryBlocker,
)
from apps.mission_control.services.session_recovery.apply_resume import apply_session_resume
from apps.mission_control.services.session_recovery.recommendation import emit_recovery_recommendation
from apps.mission_control.services.session_recovery.recovery_blockers import detect_recovery_blockers
from apps.mission_control.services.session_recovery.recovery_snapshot import build_recovery_snapshot
from apps.mission_control.services.session_recovery.resume import derive_resume_decision


def run_session_recovery_review(*, session_ids: list[int] | None = None, auto_apply_safe: bool = False) -> AutonomousSessionRecoveryRun:
    run = AutonomousSessionRecoveryRun.objects.create()
    sessions = AutonomousRuntimeSession.objects.filter(
        session_status__in=[
            AutonomousRuntimeSessionStatus.PAUSED,
            AutonomousRuntimeSessionStatus.BLOCKED,
            AutonomousRuntimeSessionStatus.RUNNING,
        ]
    ).order_by('-updated_at', '-id')
    if session_ids:
        sessions = sessions.filter(id__in=session_ids)

    considered = 0
    ready = 0
    keep_paused = 0
    manual = 0
    stop = 0
    escalate = 0

    auto_applied = 0
    for session in sessions[:80]:
        considered += 1
        snapshot = build_recovery_snapshot(session=session, recovery_run=run).snapshot
        blockers = detect_recovery_blockers(snapshot=snapshot)
        decision = derive_resume_decision(snapshot=snapshot, blockers=blockers)
        emit_recovery_recommendation(decision=decision)
        if auto_apply_safe:
            result = apply_session_resume(decision=decision, automatic=True)
            if result.record.resume_status == 'APPLIED':
                auto_applied += 1

        if decision.decision_type == AutonomousResumeDecisionType.READY_TO_RESUME:
            ready += 1
        elif decision.decision_type == AutonomousResumeDecisionType.KEEP_PAUSED:
            keep_paused += 1
        elif decision.decision_type == AutonomousResumeDecisionType.REQUIRE_MANUAL_RECOVERY_REVIEW:
            manual += 1
        elif decision.decision_type == AutonomousResumeDecisionType.STOP_SESSION_PERMANENTLY:
            stop += 1
        elif decision.decision_type == AutonomousResumeDecisionType.ESCALATE_TO_INCIDENT_REVIEW:
            escalate += 1

    run.considered_session_count = considered
    run.ready_to_resume_count = ready
    run.keep_paused_count = keep_paused
    run.manual_review_count = manual
    run.stop_recommended_count = stop
    run.incident_escalation_count = escalate
    run.recommendation_summary = (
        f'recovery-reviewed={considered} ready={ready} keep_paused={keep_paused} '
        f'manual={manual} stop={stop} escalate={escalate} auto_applied={auto_applied}'
    )
    run.completed_at = timezone.now()
    run.metadata = {'auto_apply_safe': auto_apply_safe, 'auto_applied_count': auto_applied}
    run.save(
        update_fields=[
            'considered_session_count',
            'ready_to_resume_count',
            'keep_paused_count',
            'manual_review_count',
            'stop_recommended_count',
            'incident_escalation_count',
            'recommendation_summary',
            'completed_at',
            'metadata',
            'updated_at',
        ]
    )
    return run


def build_session_recovery_summary() -> dict:
    latest_run = AutonomousSessionRecoveryRun.objects.order_by('-started_at', '-id').first()
    decisions = AutonomousResumeDecision.objects.order_by('-created_at', '-id')[:300]
    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'summary': {
            'sessions_reviewed': latest_run.considered_session_count if latest_run else 0,
            'ready_to_resume': latest_run.ready_to_resume_count if latest_run else 0,
            'keep_paused': latest_run.keep_paused_count if latest_run else 0,
            'manual_review': latest_run.manual_review_count if latest_run else 0,
            'stop_recommended': latest_run.stop_recommended_count if latest_run else 0,
            'incident_escalation': latest_run.incident_escalation_count if latest_run else 0,
        },
        'totals': {
            'recovery_runs': AutonomousSessionRecoveryRun.objects.count(),
            'snapshots': AutonomousSessionRecoverySnapshot.objects.count(),
            'blockers': AutonomousRecoveryBlocker.objects.count(),
            'decisions': AutonomousResumeDecision.objects.count(),
            'records': AutonomousResumeRecord.objects.count(),
            'recommendations': AutonomousSessionRecoveryRecommendation.objects.count(),
        },
        'decision_breakdown': {
            'keep_paused': sum(1 for decision in decisions if decision.decision_type == AutonomousResumeDecisionType.KEEP_PAUSED),
            'ready_to_resume': sum(1 for decision in decisions if decision.decision_type == AutonomousResumeDecisionType.READY_TO_RESUME),
            'resume_monitor_only': sum(1 for decision in decisions if decision.decision_type == AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE),
            'manual_review': sum(1 for decision in decisions if decision.decision_type == AutonomousResumeDecisionType.REQUIRE_MANUAL_RECOVERY_REVIEW),
            'stop': sum(1 for decision in decisions if decision.decision_type == AutonomousResumeDecisionType.STOP_SESSION_PERMANENTLY),
            'escalate': sum(1 for decision in decisions if decision.decision_type == AutonomousResumeDecisionType.ESCALATE_TO_INCIDENT_REVIEW),
        },
    }
