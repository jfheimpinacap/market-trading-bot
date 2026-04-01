from __future__ import annotations

from dataclasses import dataclass

from apps.autonomous_trader.models import (
    AutonomousLearningTriggerReason,
    AutonomousOutcomeStatus,
    AutonomousOutcomeType,
    AutonomousPostmortemTriggerReason,
    AutonomousTradeOutcome,
    AutonomousWatchStatus,
)


@dataclass
class OutcomeSelection:
    outcome: AutonomousTradeOutcome
    postmortem_reason: str | None
    learning_reason: str | None
    blockers: list[str]


def _postmortem_reason(outcome: AutonomousTradeOutcome) -> str | None:
    if outcome.outcome_status != AutonomousOutcomeStatus.CLOSED:
        return None
    if outcome.outcome_type == AutonomousOutcomeType.LOSS_EXIT:
        return AutonomousPostmortemTriggerReason.LOSS_EXIT
    if outcome.outcome_type == AutonomousOutcomeType.MANUAL_STOP:
        return AutonomousPostmortemTriggerReason.MANUAL_STOP

    watch_status = getattr(outcome.linked_watch_record, 'watch_status', '')
    if watch_status == AutonomousWatchStatus.EXIT_REVIEW_REQUIRED:
        return AutonomousPostmortemTriggerReason.EXIT_REVIEW_REQUIRED
    if getattr(outcome.linked_watch_record, 'risk_change_detected', False):
        return AutonomousPostmortemTriggerReason.RISK_DRIFT
    if getattr(outcome.linked_watch_record, 'sentiment_shift_detected', False):
        return AutonomousPostmortemTriggerReason.SENTIMENT_REVERSAL
    return None


def _learning_reason(outcome: AutonomousTradeOutcome, postmortem_reason: str | None) -> str | None:
    if outcome.outcome_status != AutonomousOutcomeStatus.CLOSED:
        return None
    if postmortem_reason:
        return AutonomousLearningTriggerReason.LOSS_REVIEW_COMPLETED
    if outcome.outcome_type == AutonomousOutcomeType.PROFITABLE_EXIT:
        return AutonomousLearningTriggerReason.PROFITABLE_PATTERN_CAPTURE
    if outcome.outcome_type == AutonomousOutcomeType.NO_ACTION:
        return AutonomousLearningTriggerReason.NO_ACTION_LESSON
    if outcome.linked_watch_record_id:
        return AutonomousLearningTriggerReason.MONITORING_LESSON
    return None


def select_outcomes_for_handoff(*, limit: int = 100) -> list[OutcomeSelection]:
    outcomes = (
        AutonomousTradeOutcome.objects.select_related(
            'linked_execution__linked_candidate',
            'linked_watch_record',
        )
        .order_by('-created_at', '-id')[:limit]
    )
    selections: list[OutcomeSelection] = []

    for outcome in outcomes:
        blockers: list[str] = []
        if outcome.outcome_status != AutonomousOutcomeStatus.CLOSED:
            blockers.append('OUTCOME_NOT_CLOSED')

        postmortem_reason = _postmortem_reason(outcome)
        learning_reason = _learning_reason(outcome, postmortem_reason)

        if outcome.outcome_status == AutonomousOutcomeStatus.CLOSED and not outcome.linked_execution_id:
            blockers.append('MISSING_EXECUTION')

        selections.append(
            OutcomeSelection(
                outcome=outcome,
                postmortem_reason=postmortem_reason,
                learning_reason=learning_reason,
                blockers=blockers,
            )
        )

    return selections
