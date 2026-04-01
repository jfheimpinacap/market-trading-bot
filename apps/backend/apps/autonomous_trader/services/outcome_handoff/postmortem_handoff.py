from __future__ import annotations

from dataclasses import dataclass

from apps.autonomous_trader.models import (
    AutonomousOutcomeHandoffStatus,
    AutonomousPostmortemHandoff,
    AutonomousTradeOutcome,
)
from apps.postmortem_agents.services.board import run_postmortem_board
from apps.postmortem_demo.services import generate_trade_review


@dataclass
class PostmortemEmitResult:
    handoff: AutonomousPostmortemHandoff
    created: bool
    duplicate_skipped: bool
    blocked: bool


def emit_postmortem_handoff(*, outcome: AutonomousTradeOutcome, trigger_reason: str, actor: str) -> PostmortemEmitResult:
    defaults = {
        'linked_execution': outcome.linked_execution,
        'linked_candidate': outcome.linked_execution.linked_candidate if outcome.linked_execution_id else None,
        'handoff_summary': f'Outcome #{outcome.id} queued for postmortem ({trigger_reason}).',
        'metadata': {'actor': actor, 'paper_only': True, 'outcome_type': outcome.outcome_type},
    }
    handoff, created = AutonomousPostmortemHandoff.objects.get_or_create(
        linked_outcome=outcome,
        trigger_reason=trigger_reason,
        defaults=defaults,
    )
    if not created:
        handoff.handoff_status = AutonomousOutcomeHandoffStatus.DUPLICATE_SKIPPED
        handoff.handoff_summary = f'Duplicate skipped for outcome #{outcome.id}.'
        handoff.save(update_fields=['handoff_status', 'handoff_summary', 'updated_at'])
        return PostmortemEmitResult(handoff=handoff, created=False, duplicate_skipped=True, blocked=False)

    trade = outcome.linked_execution.linked_paper_trade if outcome.linked_execution_id else None
    if not trade:
        handoff.handoff_status = AutonomousOutcomeHandoffStatus.BLOCKED
        handoff.handoff_summary = 'Blocked because linked paper trade is missing.'
        handoff.metadata = {**(handoff.metadata or {}), 'blocker': 'MISSING_PAPER_TRADE'}
        handoff.save(update_fields=['handoff_status', 'handoff_summary', 'metadata', 'updated_at'])
        return PostmortemEmitResult(handoff=handoff, created=True, duplicate_skipped=False, blocked=True)

    trade_review = generate_trade_review(trade, refresh_existing=True).review
    try:
        board_result = run_postmortem_board(related_trade_review_id=trade_review.id)
    except Exception as exc:  # conservative fallback when precedent stack is unavailable
        handoff.handoff_status = AutonomousOutcomeHandoffStatus.EMITTED
        handoff.handoff_summary = 'Postmortem handoff emitted; board run deferred due to local dependency limits.'
        handoff.metadata = {
            **(handoff.metadata or {}),
            'trade_review_id': trade_review.id,
            'deferred_reason': str(exc),
        }
        handoff.save(update_fields=['handoff_status', 'handoff_summary', 'metadata', 'updated_at'])
        return PostmortemEmitResult(handoff=handoff, created=True, duplicate_skipped=False, blocked=False)

    handoff.linked_postmortem_run = board_result.board_run
    handoff.handoff_status = AutonomousOutcomeHandoffStatus.COMPLETED
    handoff.handoff_summary = f'Postmortem run #{board_result.board_run.id} completed for outcome #{outcome.id}.'
    handoff.metadata = {
        **(handoff.metadata or {}),
        'trade_review_id': trade_review.id,
        'postmortem_status': board_result.board_run.status,
    }
    handoff.save(update_fields=['linked_postmortem_run', 'handoff_status', 'handoff_summary', 'metadata', 'updated_at'])
    return PostmortemEmitResult(handoff=handoff, created=True, duplicate_skipped=False, blocked=False)
