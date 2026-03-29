from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_intake.models import IntakeRecommendation, IntakeRun
from apps.autonomy_intake.services.candidates import build_intake_candidates
from apps.autonomy_intake.services.control import emit_proposal_for_backlog_item
from apps.autonomy_intake.services.dedup import find_duplicate_proposal
from apps.autonomy_intake.services.recommendation import build_intake_recommendations


@transaction.atomic
def run_intake_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_intake_candidates()
    run = IntakeRun.objects.create(metadata={'actor': actor, 'manual_first': True})

    recommendations: list[IntakeRecommendation] = []
    emitted = []

    ready_queue_size = sum(1 for row in candidates if row.ready_for_intake and not row.blockers)

    for candidate in candidates:
        duplicate = find_duplicate_proposal(backlog_item_id=candidate.backlog_item, target_scope=candidate.target_scope)
        if candidate.ready_for_intake and not duplicate:
            emitted.append(emit_proposal_for_backlog_item(backlog_item_id=candidate.backlog_item, actor=actor))
            duplicate = emitted[-1]

        for row in build_intake_recommendations(candidate=candidate, has_duplicate=duplicate is not None, queue_size=ready_queue_size):
            recommendations.append(
                IntakeRecommendation.objects.create(
                    intake_run=run,
                    backlog_item_id=candidate.backlog_item,
                    proposal=duplicate,
                    proposal_type=row['proposal_type'],
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    run.candidate_count = len(candidates)
    run.ready_count = sum(1 for row in candidates if row.ready_for_intake)
    run.blocked_count = sum(1 for row in candidates if row.blockers)
    run.emitted_count = len(emitted)
    run.duplicate_skipped_count = sum(1 for row in recommendations if row.recommendation_type == 'SKIP_DUPLICATE_PROPOSAL')
    run.roadmap_proposal_count = sum(1 for row in emitted if row.target_scope == 'roadmap')
    run.scenario_proposal_count = sum(1 for row in emitted if row.target_scope == 'scenario')
    run.program_proposal_count = sum(1 for row in emitted if row.target_scope == 'program')
    run.manager_proposal_count = sum(1 for row in emitted if row.target_scope == 'manager')
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'emitted': emitted, 'recommendations': recommendations}
