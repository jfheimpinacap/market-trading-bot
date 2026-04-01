from __future__ import annotations

from collections import Counter
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.autonomous_trader.models import (
    AutonomousOutcomeHandoffRecommendationType,
    AutonomousOutcomeHandoffRun,
)
from apps.autonomous_trader.services.outcome_handoff.handoff_selection import select_outcomes_for_handoff
from apps.autonomous_trader.services.outcome_handoff.learning_handoff import emit_learning_handoff
from apps.autonomous_trader.services.outcome_handoff.postmortem_handoff import emit_postmortem_handoff
from apps.autonomous_trader.services.outcome_handoff.recommendation import create_recommendation, recommend_wait_for_closure


@transaction.atomic
def run_outcome_handoff_engine(*, actor: str = 'operator-ui', limit: int = 100) -> AutonomousOutcomeHandoffRun:
    run = AutonomousOutcomeHandoffRun.objects.create(started_at=timezone.now(), metadata={'actor': actor, 'paper_only': True})
    selections = select_outcomes_for_handoff(limit=limit)
    rec_counter: Counter[str] = Counter()

    for selection in selections:
        run.considered_outcome_count += 1

        if 'OUTCOME_NOT_CLOSED' in selection.blockers:
            run.blocked_count += 1
            rec_counter[AutonomousOutcomeHandoffRecommendationType.WAIT_FOR_OUTCOME_CLOSURE] += 1
            recommend_wait_for_closure(outcome=selection.outcome, blockers=selection.blockers)
            continue

        emitted_postmortem = None
        if selection.postmortem_reason:
            run.eligible_postmortem_count += 1
            postmortem_result = emit_postmortem_handoff(
                outcome=selection.outcome,
                trigger_reason=selection.postmortem_reason,
                actor=actor,
            )
            emitted_postmortem = postmortem_result.handoff
            if postmortem_result.duplicate_skipped:
                run.duplicate_skipped_count += 1
                rec_counter[AutonomousOutcomeHandoffRecommendationType.BLOCK_DUPLICATE_HANDOFF] += 1
                create_recommendation(
                    recommendation_type=AutonomousOutcomeHandoffRecommendationType.BLOCK_DUPLICATE_HANDOFF,
                    target_outcome=selection.outcome,
                    target_postmortem_handoff=postmortem_result.handoff,
                    rationale='Postmortem handoff already exists for the same outcome and trigger.',
                    reason_codes=['DUPLICATE_POSTMORTEM_HANDOFF'],
                    confidence=Decimal('0.9900'),
                    blockers=['DUPLICATE_HANDOFF'],
                )
            elif postmortem_result.blocked:
                run.blocked_count += 1
                rec_counter[AutonomousOutcomeHandoffRecommendationType.REQUIRE_MANUAL_REVIEW_BEFORE_HANDOFF] += 1
                create_recommendation(
                    recommendation_type=AutonomousOutcomeHandoffRecommendationType.REQUIRE_MANUAL_REVIEW_BEFORE_HANDOFF,
                    target_outcome=selection.outcome,
                    target_postmortem_handoff=postmortem_result.handoff,
                    rationale='Missing postmortem prerequisites; manual review is required.',
                    reason_codes=['MISSING_POSTMORTEM_CONTEXT'],
                    confidence=Decimal('0.9300'),
                    blockers=['MISSING_PAPER_TRADE'],
                )
            else:
                run.postmortem_handoff_created_count += 1
                rec_counter[AutonomousOutcomeHandoffRecommendationType.SEND_TO_POSTMORTEM_NOW] += 1
                create_recommendation(
                    recommendation_type=AutonomousOutcomeHandoffRecommendationType.SEND_TO_POSTMORTEM_NOW,
                    target_outcome=selection.outcome,
                    target_postmortem_handoff=postmortem_result.handoff,
                    rationale='Closed outcome met conservative postmortem trigger and was emitted.',
                    reason_codes=[selection.postmortem_reason],
                    confidence=Decimal('0.9100'),
                    blockers=[],
                )

        if selection.learning_reason:
            run.eligible_learning_count += 1
            learning_result = emit_learning_handoff(
                outcome=selection.outcome,
                trigger_reason=selection.learning_reason,
                actor=actor,
                linked_postmortem_handoff=emitted_postmortem,
            )
            if learning_result.duplicate_skipped:
                run.duplicate_skipped_count += 1
            elif learning_result.blocked:
                run.blocked_count += 1
            else:
                run.learning_handoff_created_count += 1
                rec_counter[AutonomousOutcomeHandoffRecommendationType.SEND_TO_LEARNING_CAPTURE] += 1
                create_recommendation(
                    recommendation_type=AutonomousOutcomeHandoffRecommendationType.SEND_TO_LEARNING_CAPTURE,
                    target_outcome=selection.outcome,
                    target_learning_handoff=learning_result.handoff,
                    rationale='Learning capture was emitted with conservative paper-only integration.',
                    reason_codes=[selection.learning_reason],
                    confidence=Decimal('0.9000'),
                    blockers=[],
                )

        if emitted_postmortem and emitted_postmortem.handoff_status == 'COMPLETED':
            rec_counter[AutonomousOutcomeHandoffRecommendationType.CLOSE_FEEDBACK_LOOP] += 1
            create_recommendation(
                recommendation_type=AutonomousOutcomeHandoffRecommendationType.CLOSE_FEEDBACK_LOOP,
                target_outcome=selection.outcome,
                target_postmortem_handoff=emitted_postmortem,
                rationale='Postmortem completed; feedback loop can move to conservative reuse.',
                reason_codes=['POSTMORTEM_COMPLETED'],
                confidence=Decimal('0.8600'),
                blockers=[],
            )

    run.completed_at = timezone.now()
    run.recommendation_summary = dict(rec_counter)
    run.save(
        update_fields=[
            'completed_at',
            'considered_outcome_count',
            'eligible_postmortem_count',
            'eligible_learning_count',
            'postmortem_handoff_created_count',
            'learning_handoff_created_count',
            'duplicate_skipped_count',
            'blocked_count',
            'recommendation_summary',
            'updated_at',
        ]
    )
    return run


def build_outcome_handoff_summary() -> dict:
    latest = AutonomousOutcomeHandoffRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'latest_run_id': None,
            'considered_outcome_count': 0,
            'eligible_postmortem_count': 0,
            'eligible_learning_count': 0,
            'postmortem_handoff_created_count': 0,
            'learning_handoff_created_count': 0,
            'emitted_count': 0,
            'duplicate_skipped_count': 0,
            'blocked_count': 0,
            'recommendation_summary': {},
        }

    return {
        'latest_run_id': latest.id,
        'considered_outcome_count': latest.considered_outcome_count,
        'eligible_postmortem_count': latest.eligible_postmortem_count,
        'eligible_learning_count': latest.eligible_learning_count,
        'postmortem_handoff_created_count': latest.postmortem_handoff_created_count,
        'learning_handoff_created_count': latest.learning_handoff_created_count,
        'emitted_count': latest.postmortem_handoff_created_count + latest.learning_handoff_created_count,
        'duplicate_skipped_count': latest.duplicate_skipped_count,
        'blocked_count': latest.blocked_count,
        'recommendation_summary': latest.recommendation_summary,
    }
