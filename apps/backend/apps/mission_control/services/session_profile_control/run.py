from __future__ import annotations

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousProfileSelectionRun,
    AutonomousProfileSwitchDecision,
    AutonomousProfileSwitchDecisionType,
    AutonomousProfileSwitchRecord,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionContextReview,
)
from apps.mission_control.services.session_profile_control.context_review import build_session_context_review
from apps.mission_control.services.session_profile_control.profile_switch import apply_profile_switch_decision, decide_profile_switch
from apps.mission_control.services.session_profile_control.recommendation import emit_profile_recommendation


def run_profile_selection_review(*, session_ids: list[int] | None = None, apply_switches: bool = True) -> AutonomousProfileSelectionRun:
    sessions = AutonomousRuntimeSession.objects.filter(
        session_status__in=[
            AutonomousRuntimeSessionStatus.RUNNING,
            AutonomousRuntimeSessionStatus.PAUSED,
            AutonomousRuntimeSessionStatus.BLOCKED,
        ]
    ).select_related('linked_schedule_profile').order_by('-started_at', '-id')
    if session_ids:
        sessions = sessions.filter(id__in=session_ids)
    sessions = sessions[:60]

    run = AutonomousProfileSelectionRun.objects.create(started_at=timezone.now(), considered_session_count=sessions.count())

    keep_count = 0
    switch_recommended = 0
    switched_count = 0
    blocked_count = 0
    manual_review = 0

    for session in sessions:
        context = build_session_context_review(session=session, selection_run=run)
        decision = decide_profile_switch(session=session, context_review=context.review, selection_run=run)
        emit_profile_recommendation(decision=decision)

        if decision.decision_type == AutonomousProfileSwitchDecisionType.KEEP_CURRENT_PROFILE:
            keep_count += 1
        elif decision.decision_type in {
            AutonomousProfileSwitchDecisionType.SWITCH_TO_BALANCED_LOCAL,
            AutonomousProfileSwitchDecisionType.SWITCH_TO_CONSERVATIVE_QUIET,
            AutonomousProfileSwitchDecisionType.SWITCH_TO_MONITOR_HEAVY,
        }:
            switch_recommended += 1
        elif decision.decision_type == AutonomousProfileSwitchDecisionType.BLOCK_PROFILE_SWITCH:
            blocked_count += 1
        else:
            manual_review += 1

        if apply_switches:
            record = apply_profile_switch_decision(decision=decision, automatic=True)
            if record:
                switched_count += 1

    run.keep_current_profile_count = keep_count
    run.switch_recommended_count = switch_recommended
    run.switched_count = switched_count
    run.blocked_switch_count = blocked_count
    run.completed_at = timezone.now()
    run.recommendation_summary = (
        f'keep={keep_count} switch_recommended={switch_recommended} switched={switched_count} '
        f'blocked={blocked_count} manual={manual_review}'
    )
    run.metadata = {'manual_review_count': manual_review, 'apply_switches': apply_switches}
    run.save(
        update_fields=[
            'keep_current_profile_count',
            'switch_recommended_count',
            'switched_count',
            'blocked_switch_count',
            'completed_at',
            'recommendation_summary',
            'metadata',
            'updated_at',
        ]
    )
    return run


def build_profile_selection_summary(*, extra: dict | None = None) -> dict:
    latest_run = AutonomousProfileSelectionRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run': latest_run.id if latest_run else None,
        'summary': {
            'sessions_reviewed': latest_run.considered_session_count if latest_run else 0,
            'keep_current': latest_run.keep_current_profile_count if latest_run else 0,
            'switch_recommended': latest_run.switch_recommended_count if latest_run else 0,
            'switched': latest_run.switched_count if latest_run else 0,
            'blocked': latest_run.blocked_switch_count if latest_run else 0,
            'manual_review': int((latest_run.metadata or {}).get('manual_review_count', 0)) if latest_run else 0,
        },
        'totals': {
            'runs': AutonomousProfileSelectionRun.objects.count(),
            'context_reviews': AutonomousSessionContextReview.objects.count(),
            'switch_decisions': AutonomousProfileSwitchDecision.objects.count(),
            'switch_records': AutonomousProfileSwitchRecord.objects.count(),
        },
    } | ({'extra': extra} if extra else {})
