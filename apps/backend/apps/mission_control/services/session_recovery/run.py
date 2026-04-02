from __future__ import annotations

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousRecoveryBlocker,
    AutonomousRecoveryBlockerStatus,
    AutonomousResumeAppliedMode,
    AutonomousResumeDecision,
    AutonomousResumeDecisionStatus,
    AutonomousResumeDecisionType,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionHealthStatus,
    AutonomousSessionRecoveryRecommendation,
    AutonomousSessionRecoveryRecommendationType,
    AutonomousSessionRecoveryRun,
    AutonomousSessionRecoverySnapshot,
    AutonomousSessionRecoveryStatus,
    AutonomousSessionTimingSnapshot,
)
from apps.mission_control.services.session_recovery.apply_resume import apply_resume_decision


def run_session_recovery_review(*, session_ids: list[int] | None = None, auto_apply_safe: bool = False) -> AutonomousSessionRecoveryRun:
    run = AutonomousSessionRecoveryRun.objects.create(metadata={'auto_apply_safe': auto_apply_safe})

    sessions = AutonomousRuntimeSession.objects.filter(
        session_status__in=[
            AutonomousRuntimeSessionStatus.PAUSED,
            AutonomousRuntimeSessionStatus.BLOCKED,
            AutonomousRuntimeSessionStatus.DEGRADED,
        ]
    ).order_by('-updated_at', '-id')
    if session_ids:
        sessions = sessions.filter(id__in=session_ids)

    considered = blocked = ready = monitor = manual = applied = 0

    for session in sessions[:80]:
        considered += 1
        health = AutonomousSessionHealthSnapshot.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
        timing = AutonomousSessionTimingSnapshot.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
        blockers = list(
            AutonomousRecoveryBlocker.objects.filter(
                linked_session=session,
                blocker_status=AutonomousRecoveryBlockerStatus.ACTIVE,
            ).values_list('blocker_type', flat=True)
        )
        has_blockers = bool(blockers)

        recovery_status = AutonomousSessionRecoveryStatus.STABLE
        reason_codes: list[str] = []

        if has_blockers:
            recovery_status = AutonomousSessionRecoveryStatus.BLOCKED
            reason_codes.append('active_blockers')
        elif health and health.session_health_status in {
            AutonomousSessionHealthStatus.BLOCKED,
            AutonomousSessionHealthStatus.STALLED,
            AutonomousSessionHealthStatus.DEGRADED,
        }:
            recovery_status = AutonomousSessionRecoveryStatus.DEGRADED
            reason_codes.append('health_degraded')
        elif session.session_status in {AutonomousRuntimeSessionStatus.BLOCKED, AutonomousRuntimeSessionStatus.DEGRADED}:
            recovery_status = AutonomousSessionRecoveryStatus.AMBIGUOUS
            reason_codes.append('session_status_ambiguous')

        snapshot = AutonomousSessionRecoverySnapshot.objects.create(
            linked_recovery_run=run,
            linked_session=session,
            linked_health_snapshot=health,
            linked_timing_snapshot=timing,
            recovery_status=recovery_status,
            recovery_summary=f'Recovery snapshot for session={session.id}.',
            reason_codes=reason_codes,
            metadata={
                'active_blockers': blockers,
                'session_status': session.session_status,
                'timing_status': timing.timing_status if timing else None,
            },
        )

        decision_type = AutonomousResumeDecisionType.READY_TO_RESUME
        auto_applicable = True

        if has_blockers:
            decision_type = AutonomousResumeDecisionType.KEEP_PAUSED
            auto_applicable = False
            blocked += 1
        elif recovery_status in {AutonomousSessionRecoveryStatus.DEGRADED, AutonomousSessionRecoveryStatus.AMBIGUOUS}:
            decision_type = AutonomousResumeDecisionType.REQUIRE_MANUAL_REVIEW
            auto_applicable = False
            manual += 1
        elif timing and timing.timing_status == 'MONITOR_ONLY_WINDOW':
            decision_type = AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE
            auto_applicable = True
            monitor += 1
        else:
            ready += 1

        decision = AutonomousResumeDecision.objects.create(
            linked_session=session,
            linked_recovery_run=run,
            linked_recovery_snapshot=snapshot,
            decision_type=decision_type,
            decision_status=AutonomousResumeDecisionStatus.PROPOSED,
            auto_applicable=auto_applicable,
            decision_summary=f'Resume decision={decision_type} for session={session.id}.',
            reason_codes=reason_codes,
            metadata={'active_blockers': blockers},
        )

        if auto_apply_safe and decision.decision_type == AutonomousResumeDecisionType.READY_TO_RESUME and decision.auto_applicable:
            result = apply_resume_decision(
                decision=decision,
                applied_mode=AutonomousResumeAppliedMode.AUTO_SAFE_RESUME,
                automatic=True,
            )
            if result.record.resume_status == 'APPLIED':
                applied += 1

        if decision_type == AutonomousResumeDecisionType.READY_TO_RESUME:
            AutonomousSessionRecoveryRecommendation.objects.create(
                recommendation_type=AutonomousSessionRecoveryRecommendationType.SAFE_AUTO_RESUME,
                target_session=session,
                target_recovery_snapshot=snapshot,
                target_resume_decision=decision,
                rationale='Session is paused and appears healthy enough for conservative resume.',
                reason_codes=reason_codes,
                confidence=0.7,
                blockers=blockers,
            )
        elif decision_type == AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE:
            AutonomousSessionRecoveryRecommendation.objects.create(
                recommendation_type=AutonomousSessionRecoveryRecommendationType.RESUME_IN_MONITOR_ONLY,
                target_session=session,
                target_recovery_snapshot=snapshot,
                target_resume_decision=decision,
                rationale='Resume is possible but should use monitor-only runtime posture.',
                reason_codes=reason_codes,
                confidence=0.7,
                blockers=blockers,
            )
        elif decision_type == AutonomousResumeDecisionType.KEEP_PAUSED:
            AutonomousSessionRecoveryRecommendation.objects.create(
                recommendation_type=AutonomousSessionRecoveryRecommendationType.KEEP_PAUSED_PENDING_REVIEW,
                target_session=session,
                target_recovery_snapshot=snapshot,
                target_resume_decision=decision,
                rationale='Active blockers must be resolved before any resume action.',
                reason_codes=reason_codes,
                confidence=0.9,
                blockers=blockers,
            )
        else:
            AutonomousSessionRecoveryRecommendation.objects.create(
                recommendation_type=AutonomousSessionRecoveryRecommendationType.REQUIRE_MANUAL_RECOVERY_REVIEW,
                target_session=session,
                target_recovery_snapshot=snapshot,
                target_resume_decision=decision,
                rationale='Recovery signal is degraded/ambiguous and manual review is safer.',
                reason_codes=reason_codes,
                confidence=0.8,
                blockers=blockers,
            )

    run.considered_session_count = considered
    run.blocked_count = blocked
    run.ready_to_resume_count = ready
    run.monitor_only_resume_count = monitor
    run.manual_review_count = manual
    run.applied_resume_count = applied
    run.recommendation_summary = (
        f'reviewed={considered} ready={ready} monitor={monitor} blocked={blocked} manual={manual} auto_applied={applied}'
    )
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            'considered_session_count',
            'blocked_count',
            'ready_to_resume_count',
            'monitor_only_resume_count',
            'manual_review_count',
            'applied_resume_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )
    return run


def build_session_recovery_summary() -> dict:
    latest_run = AutonomousSessionRecoveryRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'summary': {
            'sessions_reviewed': latest_run.considered_session_count if latest_run else 0,
            'ready_to_resume': latest_run.ready_to_resume_count if latest_run else 0,
            'monitor_only_resume': latest_run.monitor_only_resume_count if latest_run else 0,
            'blocked': latest_run.blocked_count if latest_run else 0,
            'manual_review': latest_run.manual_review_count if latest_run else 0,
            'applied_resume': latest_run.applied_resume_count if latest_run else 0,
        },
    }
