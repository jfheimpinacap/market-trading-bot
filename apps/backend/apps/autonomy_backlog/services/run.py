from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_backlog.models import (
    BacklogRecommendation,
    BacklogRun,
    GovernanceBacklogStatus,
)
from apps.autonomy_backlog.services.candidates import build_backlog_candidates
from apps.autonomy_backlog.services.control import create_backlog_item
from apps.autonomy_backlog.services.dedup import find_duplicate_backlog_item
from apps.autonomy_backlog.services.recommendation import build_backlog_recommendations


@transaction.atomic
def run_backlog_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_backlog_candidates()
    run = BacklogRun.objects.create(metadata={'actor': actor})

    recommendations: list[BacklogRecommendation] = []
    created_items = []

    ready_queue_size = sum(1 for row in candidates if row.ready_for_backlog and not row.blockers)

    for candidate in candidates:
        duplicate = find_duplicate_backlog_item(artifact_id=candidate.advisory_artifact)
        if candidate.ready_for_backlog and not duplicate and not candidate.blockers:
            created_items.append(create_backlog_item(artifact_id=candidate.advisory_artifact, actor=actor))
            duplicate = created_items[-1]

        for row in build_backlog_recommendations(
            candidate=candidate,
            has_duplicate=duplicate is not None,
            existing_status=duplicate.backlog_status if duplicate else None,
            queue_size=ready_queue_size,
        ):
            recommendations.append(
                BacklogRecommendation.objects.create(
                    backlog_run=run,
                    advisory_artifact_id=candidate.advisory_artifact,
                    insight_id=candidate.insight,
                    backlog_item=duplicate,
                    recommendation_type=row['recommendation_type'],
                    backlog_type=duplicate.backlog_type if duplicate else '',
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    run.candidate_count = len(candidates)
    run.ready_count = sum(1 for row in candidates if row.ready_for_backlog)
    run.blocked_count = sum(1 for row in candidates if row.blockers)
    run.created_count = len(created_items)
    run.duplicate_skipped_count = sum(1 for row in recommendations if row.recommendation_type == 'SKIP_DUPLICATE_BACKLOG')
    run.prioritized_count = sum(1 for row in recommendations if row.recommendation_type == 'PRIORITIZE_BACKLOG_ITEM')
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.metadata = {
        **(run.metadata or {}),
        'ready_but_not_prioritized': sum(
            1 for item in created_items if item.backlog_status in {GovernanceBacklogStatus.PENDING_REVIEW, GovernanceBacklogStatus.READY}
        ),
    }
    run.save()

    return {'run': run, 'candidates': candidates, 'created_items': created_items, 'recommendations': recommendations}
