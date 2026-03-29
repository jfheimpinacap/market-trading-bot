from __future__ import annotations

from collections import Counter

from apps.autonomy_program.models import AutonomyProgramState
from apps.autonomy_recovery.services.candidates import RecoveryCandidateContext


def collect_blockers(context: RecoveryCandidateContext) -> dict:
    blockers: list[str] = []
    blocker_types: Counter[str] = Counter()

    if context.pending_approvals_count > 0:
        blockers.append('pending_approvals')
        blocker_types['approval'] += context.pending_approvals_count
    if context.pending_checkpoints_count > 0:
        blockers.append('pending_checkpoints')
        blocker_types['checkpoint'] += context.pending_checkpoints_count
    if context.incident_impact > 0:
        blockers.append('incident_pressure')
        blocker_types['incident'] += context.incident_impact
    if context.degraded_impact > 0:
        blockers.append('degraded_pressure')
        blocker_types['degraded'] += context.degraded_impact
    if context.campaign.status == 'BLOCKED':
        blockers.append('campaign_blocked')
        blocker_types['campaign_status'] += 1

    program = AutonomyProgramState.objects.order_by('-created_at', '-id').first()
    if program and program.concurrency_posture == 'FROZEN':
        blockers.append('program_frozen')
        blocker_types['program'] += 1
    domains = set((context.campaign.metadata or {}).get('domains', []))
    locked = set((program.locked_domains if program else []) or [])
    if domains.intersection(locked):
        blockers.append('locked_domain_conflict')
        blocker_types['domain_conflict'] += len(domains.intersection(locked))

    return {
        'blockers': sorted(set(blockers)),
        'blocker_count': sum(blocker_types.values()),
        'blocker_types': dict(blocker_types),
        'program_posture': program.concurrency_posture if program else None,
    }
