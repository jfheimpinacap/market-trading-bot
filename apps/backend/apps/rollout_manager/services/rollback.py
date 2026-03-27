from __future__ import annotations

from django.utils import timezone

from apps.rollout_manager.models import RolloutDecision, RolloutDecisionCode, StackRolloutRun, StackRolloutRunStatus


def rollback_run(*, run: StackRolloutRun, reason: str, actor: str = 'operator') -> StackRolloutRun:
    run.status = StackRolloutRunStatus.ROLLED_BACK
    run.finished_at = timezone.now()
    run.current_phase = 'ROLLED_BACK_TO_CHAMPION_ONLY'
    run.summary = f'Rollout rolled back to champion-only route. Reason: {reason}'
    run.metadata = {
        **(run.metadata or {}),
        'rollback': {
            'reason': reason,
            'actor': actor,
            'executed_at': timezone.now().isoformat(),
            'paper_demo_only': True,
        },
    }
    run.save(update_fields=['status', 'finished_at', 'current_phase', 'summary', 'metadata', 'updated_at'])

    RolloutDecision.objects.create(
        run=run,
        decision=RolloutDecisionCode.ROLLBACK_NOW,
        rationale=reason,
        reason_codes=['MANUAL_ROLLBACK'],
        actor=actor,
        recommendation_payload={'rollback_applied': True},
    )
    return run
