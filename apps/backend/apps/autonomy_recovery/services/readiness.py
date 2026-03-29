from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.autonomy_recovery.services.blockers import collect_blockers
from apps.autonomy_recovery.services.candidates import RecoveryCandidateContext


def evaluate_recovery_readiness(context: RecoveryCandidateContext) -> dict:
    blocker_data = collect_blockers(context)
    blockers = blocker_data['blockers']
    paused_since = context.campaign.updated_at
    paused_duration_seconds = None
    if paused_since:
        paused_duration_seconds = max(0, int((timezone.now() - paused_since).total_seconds()))

    score = 100
    score -= context.pending_approvals_count * 20
    score -= context.pending_checkpoints_count * 15
    score -= context.incident_impact * 15
    score -= context.degraded_impact * 20
    if 'program_frozen' in blockers or 'locked_domain_conflict' in blockers:
        score -= 40
    if context.campaign.status == 'BLOCKED':
        score -= 25

    score = max(0, min(100, score))
    incident_pressure = context.incident_impact + context.degraded_impact

    if score >= 75 and not blockers:
        readiness = 'READY'
        recovery_status = 'READY_TO_RESUME'
        rationale = 'Campaign is clean: no open blockers, no pending approvals/checkpoints, and low pressure.'
    elif 'program_frozen' in blockers or 'locked_domain_conflict' in blockers or context.campaign.status == 'BLOCKED':
        readiness = 'NOT_READY'
        recovery_status = 'BLOCKED'
        rationale = 'Global posture/domain conflict or campaign blocked status prevents safe resume.'
    elif paused_duration_seconds and paused_duration_seconds > int(timedelta(hours=24).total_seconds()) and incident_pressure >= 2:
        readiness = 'NOT_READY'
        recovery_status = 'CLOSE_CANDIDATE'
        rationale = 'Campaign remained paused for extended duration with sustained pressure; closure candidate.'
    elif incident_pressure >= 2:
        readiness = 'NOT_READY'
        recovery_status = 'REVIEW_ABORT'
        rationale = 'Incident/degraded pressure remains elevated; review for abort is safer than resume.'
    elif context.pending_approvals_count > 0 or context.pending_checkpoints_count > 0:
        readiness = 'CAUTION'
        recovery_status = 'KEEP_PAUSED'
        rationale = 'Approval/checkpoint blockers still open; keep paused until cleared.'
    else:
        readiness = 'CAUTION'
        recovery_status = 'RECOVERY_IN_PROGRESS'
        rationale = 'Recovery is progressing but requires more evidence before resume.'

    recovery_priority = max(1, 100 - score + min(40, incident_pressure * 10))

    return {
        **blocker_data,
        'paused_duration_seconds': paused_duration_seconds,
        'incident_pressure_level': incident_pressure,
        'recovery_score': score,
        'resume_readiness': readiness,
        'recovery_status': recovery_status,
        'recovery_priority': recovery_priority,
        'rationale': rationale,
    }
