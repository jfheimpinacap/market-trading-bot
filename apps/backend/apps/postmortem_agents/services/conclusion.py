from __future__ import annotations

from decimal import Decimal

from apps.learning_memory.models import LearningMemoryEntry, LearningMemoryType, LearningOutcome, LearningSourceType
from apps.learning_memory.services.integration import run_learning_rebuild
from apps.postmortem_agents.models import PostmortemBoardConclusion


def build_board_conclusion(*, board_run, perspective_reviews: list) -> PostmortemBoardConclusion:
    modes: list[str] = []
    for review in perspective_reviews:
        perspective = review.perspective_type
        confidence = Decimal(str(review.confidence or 0))
        if confidence >= Decimal('0.6500'):
            modes.append(perspective)

    primary_failure_mode = modes[0] if modes else 'mixed'
    secondary = modes[1:4] if len(modes) > 1 else []
    severity = 'high' if board_run.related_trade_review.outcome == 'UNFAVORABLE' else 'medium'

    recommended_adjustments: list[str] = []
    for review in perspective_reviews:
        for action in review.recommended_actions[:2]:
            if action not in recommended_adjustments:
                recommended_adjustments.append(action)

    return PostmortemBoardConclusion.objects.create(
        board_run=board_run,
        primary_failure_mode=primary_failure_mode,
        secondary_failure_modes=secondary,
        lesson_learned=f'Primary mode: {primary_failure_mode}. Use evidence-backed conservative adjustments before repeating this setup.',
        recommended_adjustments=recommended_adjustments[:8],
        should_update_learning_memory=board_run.related_trade_review.outcome == 'UNFAVORABLE',
        severity=severity,
        metadata={
            'perspectives': [review.perspective_type for review in perspective_reviews],
            'statuses': [review.status for review in perspective_reviews],
        },
    )


def apply_learning_handoff(*, conclusion: PostmortemBoardConclusion, force_rebuild: bool = False) -> dict:
    review = conclusion.board_run.related_trade_review
    created_note = None
    if conclusion.should_update_learning_memory:
        created_note = LearningMemoryEntry.objects.create(
            memory_type=LearningMemoryType.TRADE_PATTERN,
            source_type=LearningSourceType.DEMO if review.market.source_type == 'demo' else LearningSourceType.REAL_READ_ONLY,
            provider=review.market.provider,
            market=review.market,
            related_trade=review.paper_trade,
            related_review=review,
            outcome=LearningOutcome.NEGATIVE if review.outcome == 'UNFAVORABLE' else LearningOutcome.NEUTRAL,
            score_delta=Decimal('-6.00') if review.outcome == 'UNFAVORABLE' else Decimal('-1.00'),
            confidence_delta=Decimal('-0.0300'),
            quantity_bias_delta=Decimal('-0.0800') if review.outcome == 'UNFAVORABLE' else Decimal('-0.0200'),
            summary=f'Board conclusion #{conclusion.id}: {conclusion.primary_failure_mode}',
            rationale=conclusion.lesson_learned,
            metadata={
                'board_run_id': conclusion.board_run_id,
                'conclusion_id': conclusion.id,
                'recommended_adjustments': conclusion.recommended_adjustments,
            },
        )

    rebuild_run = None
    if force_rebuild or conclusion.should_update_learning_memory:
        rebuild_run = run_learning_rebuild(triggered_from='postmortem')

    return {
        'learning_memory_entry_id': created_note.id if created_note else None,
        'learning_rebuild_run_id': rebuild_run.id if rebuild_run else None,
        'learning_rebuild_status': rebuild_run.status if rebuild_run else None,
    }
