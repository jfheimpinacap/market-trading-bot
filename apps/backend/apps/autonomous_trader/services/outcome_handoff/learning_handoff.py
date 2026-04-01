from __future__ import annotations

from dataclasses import dataclass

from apps.autonomous_trader.models import (
    AutonomousLearningHandoff,
    AutonomousOutcomeHandoffStatus,
    AutonomousPostmortemHandoff,
    AutonomousTradeOutcome,
)
from apps.learning_memory.services.run import run_postmortem_learning_loop


@dataclass
class LearningEmitResult:
    handoff: AutonomousLearningHandoff
    created: bool
    duplicate_skipped: bool
    blocked: bool


def emit_learning_handoff(
    *,
    outcome: AutonomousTradeOutcome,
    trigger_reason: str,
    actor: str,
    linked_postmortem_handoff: AutonomousPostmortemHandoff | None = None,
) -> LearningEmitResult:
    handoff, created = AutonomousLearningHandoff.objects.get_or_create(
        linked_outcome=outcome,
        trigger_reason=trigger_reason,
        defaults={
            'linked_postmortem_handoff': linked_postmortem_handoff,
            'handoff_summary': f'Outcome #{outcome.id} queued for learning capture ({trigger_reason}).',
            'metadata': {'actor': actor, 'paper_only': True, 'outcome_type': outcome.outcome_type},
        },
    )
    if not created:
        handoff.handoff_status = AutonomousOutcomeHandoffStatus.DUPLICATE_SKIPPED
        handoff.handoff_summary = f'Duplicate skipped for outcome #{outcome.id} learning handoff.'
        handoff.save(update_fields=['handoff_status', 'handoff_summary', 'updated_at'])
        return LearningEmitResult(handoff=handoff, created=False, duplicate_skipped=True, blocked=False)

    if linked_postmortem_handoff and not linked_postmortem_handoff.linked_postmortem_run_id:
        handoff.handoff_status = AutonomousOutcomeHandoffStatus.BLOCKED
        handoff.handoff_summary = 'Blocked because linked postmortem run is unavailable.'
        handoff.metadata = {**(handoff.metadata or {}), 'blocker': 'MISSING_POSTMORTEM_RUN'}
        handoff.save(update_fields=['handoff_status', 'handoff_summary', 'metadata', 'updated_at'])
        return LearningEmitResult(handoff=handoff, created=True, duplicate_skipped=False, blocked=True)

    learning_run = run_postmortem_learning_loop(
        linked_postmortem_run_id=linked_postmortem_handoff.linked_postmortem_run_id if linked_postmortem_handoff else None
    )
    handoff.linked_learning_run = learning_run
    handoff.handoff_status = AutonomousOutcomeHandoffStatus.COMPLETED
    handoff.handoff_summary = f'Learning run #{learning_run.id} captured outcome #{outcome.id}.'
    handoff.metadata = {**(handoff.metadata or {}), 'learning_recommendation_summary': learning_run.recommendation_summary}
    handoff.save(update_fields=['linked_learning_run', 'handoff_status', 'handoff_summary', 'metadata', 'updated_at'])
    return LearningEmitResult(handoff=handoff, created=True, duplicate_skipped=False, blocked=False)
