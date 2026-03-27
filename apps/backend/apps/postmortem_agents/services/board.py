from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.postmortem_agents.models import (
    PostmortemAgentReview,
    PostmortemBoardRun,
    PostmortemBoardRunStatus,
    PostmortemPerspectiveType,
)
from apps.postmortem_agents.services.conclusion import apply_learning_handoff, build_board_conclusion
from apps.postmortem_agents.services.context import build_board_context
from apps.postmortem_agents.services.precedent_enrichment import build_postmortem_precedent_context
from apps.postmortem_agents.services.reviewers import (
    run_learning_review,
    run_narrative_review,
    run_prediction_review,
    run_risk_review,
    run_runtime_review,
)
from apps.postmortem_demo.models import TradeReview


@dataclass
class PostmortemBoardResult:
    board_run: PostmortemBoardRun


@transaction.atomic
def run_postmortem_board(*, related_trade_review_id: int, force_learning_rebuild: bool = False) -> PostmortemBoardResult:
    review = TradeReview.objects.select_related('paper_trade', 'market', 'market__provider').get(pk=related_trade_review_id)
    board_run = PostmortemBoardRun.objects.create(
        related_trade_review=review,
        status=PostmortemBoardRunStatus.RUNNING,
        started_at=timezone.now(),
        details={'force_learning_rebuild': force_learning_rebuild},
    )

    context = build_board_context(review)
    precedent_context = build_postmortem_precedent_context(board_run=board_run)
    review_payloads: list[dict] = []

    ordered_reviewers = [
        (PostmortemPerspectiveType.NARRATIVE, run_narrative_review),
        (PostmortemPerspectiveType.PREDICTION, run_prediction_review),
        (PostmortemPerspectiveType.RISK, run_risk_review),
        (PostmortemPerspectiveType.RUNTIME, run_runtime_review),
    ]

    for perspective, fn in ordered_reviewers:
        payload = fn(context)
        payload['key_findings'] = {
            **(payload.get('key_findings') or {}),
            'precedent_context': precedent_context,
        }
        payload['conclusion'] = f"{payload.get('conclusion', '')} {precedent_context.get('rationale_note')}".strip()
        model = PostmortemAgentReview.objects.create(
            board_run=board_run,
            perspective_type=perspective,
            **payload,
        )
        review_payloads.append({'perspective_type': perspective, 'status': model.status})

    learning_payload = run_learning_review(context, review_payloads)
    learning_payload['key_findings'] = {
        **(learning_payload.get('key_findings') or {}),
        'precedent_context': precedent_context,
    }
    learning_review = PostmortemAgentReview.objects.create(
        board_run=board_run,
        perspective_type=PostmortemPerspectiveType.LEARNING,
        **learning_payload,
    )

    perspective_reviews = list(board_run.perspective_reviews.order_by('created_at', 'id'))
    conclusion = build_board_conclusion(board_run=board_run, perspective_reviews=perspective_reviews)
    learning_handoff = apply_learning_handoff(conclusion=conclusion, force_rebuild=force_learning_rebuild)

    failed_count = sum(1 for item in perspective_reviews if item.status == 'FAILED')
    partial_count = sum(1 for item in perspective_reviews if item.status == 'PARTIAL')

    board_run.status = (
        PostmortemBoardRunStatus.FAILED
        if failed_count == len(perspective_reviews)
        else PostmortemBoardRunStatus.PARTIAL
        if failed_count > 0 or partial_count > 0
        else PostmortemBoardRunStatus.SUCCESS
    )
    board_run.finished_at = timezone.now()
    board_run.perspectives_run_count = len(perspective_reviews)
    board_run.summary = (
        f'Board reviewed trade review #{review.id}: primary failure mode={conclusion.primary_failure_mode}, '
        f'severity={conclusion.severity}, status={board_run.status}.'
    )
    board_run.details = {
        **board_run.details,
        'review_ids': [item.id for item in perspective_reviews],
        'conclusion_id': conclusion.id,
        'learning_handoff': learning_handoff,
        'learning_review_id': learning_review.id,
        'precedent_context': precedent_context,
    }
    board_run.save(
        update_fields=[
            'status',
            'finished_at',
            'perspectives_run_count',
            'summary',
            'details',
            'updated_at',
        ]
    )

    return PostmortemBoardResult(board_run=board_run)
