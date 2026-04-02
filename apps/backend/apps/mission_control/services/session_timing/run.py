from __future__ import annotations

from apps.mission_control.models import (
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousScheduleProfile,
    AutonomousSessionTimingSnapshot,
    AutonomousTimingDecision,
    AutonomousTimingRecommendation,
    AutonomousTimingStatus,
)
from apps.mission_control.services.session_timing.recommendation import emit_timing_recommendation
from apps.mission_control.services.session_timing.stop_conditions import evaluate_stop_conditions
from apps.mission_control.services.session_timing.timing import evaluate_session_timing


def run_session_timing_review(*, session_ids: list[int] | None = None) -> dict:
    sessions = AutonomousRuntimeSession.objects.filter(
        session_status__in=[
            AutonomousRuntimeSessionStatus.RUNNING,
            AutonomousRuntimeSessionStatus.PAUSED,
            AutonomousRuntimeSessionStatus.BLOCKED,
        ]
    ).order_by('-started_at', '-id')
    if session_ids:
        sessions = sessions.filter(id__in=session_ids)

    reviewed = 0
    for session in sessions[:60]:
        result = evaluate_session_timing(session=session)
        evaluate_stop_conditions(snapshot=result.snapshot, decision_type=result.decision.decision_type)
        emit_timing_recommendation(snapshot=result.snapshot, decision=result.decision)
        reviewed += 1

    return build_session_timing_summary(extra={'reviewed_now': reviewed})


def build_session_timing_summary(*, extra: dict | None = None) -> dict:
    latest_snapshots = list(AutonomousSessionTimingSnapshot.objects.select_related('linked_session').order_by('-created_at', '-id')[:400])
    latest_by_session: dict[int, AutonomousSessionTimingSnapshot] = {}
    for snapshot in latest_snapshots:
        if snapshot.linked_session_id not in latest_by_session:
            latest_by_session[snapshot.linked_session_id] = snapshot

    counts = {
        'sessions_evaluated': len(latest_by_session),
        'due_now': 0,
        'waiting_short': 0,
        'waiting_long': 0,
        'monitor_only': 0,
        'pause_recommended': 0,
        'stop_recommended': 0,
    }
    for snapshot in latest_by_session.values():
        status = snapshot.timing_status
        if status == AutonomousTimingStatus.DUE_NOW:
            counts['due_now'] += 1
        elif status == AutonomousTimingStatus.WAIT_SHORT:
            counts['waiting_short'] += 1
        elif status == AutonomousTimingStatus.WAIT_LONG:
            counts['waiting_long'] += 1
        elif status == AutonomousTimingStatus.MONITOR_ONLY_WINDOW:
            counts['monitor_only'] += 1
        elif status == AutonomousTimingStatus.PAUSE_RECOMMENDED:
            counts['pause_recommended'] += 1
        elif status == AutonomousTimingStatus.STOP_RECOMMENDED:
            counts['stop_recommended'] += 1

    payload = {
        'summary': counts,
        'total_profiles': AutonomousScheduleProfile.objects.filter(is_active=True).count(),
        'latest_snapshot_id': latest_snapshots[0].id if latest_snapshots else None,
        'latest_decision_id': AutonomousTimingDecision.objects.order_by('-created_at', '-id').values_list('id', flat=True).first(),
        'latest_recommendation_id': AutonomousTimingRecommendation.objects.order_by('-created_at', '-id').values_list('id', flat=True).first(),
    }
    if extra:
        payload['extra'] = extra
    return payload
