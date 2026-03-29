from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_followup.models import FollowupRecommendation, FollowupRecommendationType, FollowupRun
from apps.autonomy_followup.services.candidates import build_followup_candidates
from apps.autonomy_followup.services.recommendation import build_candidate_recommendations


@transaction.atomic
def run_followup_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_followup_candidates()
    run = FollowupRun.objects.create(metadata={'actor': actor})

    recommendations: list[FollowupRecommendation] = []
    for candidate in candidates:
        candidate_rows = build_candidate_recommendations(candidate)
        for row in candidate_rows:
            recommendations.append(
                FollowupRecommendation.objects.create(
                    followup_run=run,
                    target_campaign_id=candidate.campaign_id,
                    recommendation_type=row['recommendation_type'],
                    followup_type=row['followup_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata={'actor': actor, 'closeout_report_id': candidate.closeout_report_id},
                )
            )

    ready_candidates = [row for row in candidates if row.followup_readiness in {'READY', 'PARTIAL'}]
    if len(ready_candidates) > 1:
        recommendations.append(
            FollowupRecommendation.objects.create(
                followup_run=run,
                recommendation_type=FollowupRecommendationType.REORDER_FOLLOWUP_PRIORITY,
                followup_type='',
                rationale='Multiple campaigns are ready for manual follow-up; prioritize by incident pressure first.',
                reason_codes=['multiple_ready_followups'],
                confidence=0.7,
                blockers=[],
                metadata={'actor': actor, 'campaign_ids': [row.campaign_id for row in ready_candidates]},
            )
        )

    run.candidate_count = len(candidates)
    run.ready_count = sum(1 for row in candidates if row.followup_readiness in {'READY', 'PARTIAL'})
    run.blocked_count = sum(1 for row in candidates if row.followup_readiness == 'BLOCKED')
    run.emitted_count = sum(1 for row in candidates if row.followup_readiness == 'ALREADY_EMITTED')
    run.duplicate_skipped_count = sum(1 for row in recommendations if row.recommendation_type == FollowupRecommendationType.SKIP_DUPLICATE_FOLLOWUP)
    run.memory_followup_count = sum(1 for row in candidates if row.requires_memory_index)
    run.postmortem_followup_count = sum(1 for row in candidates if row.requires_postmortem)
    run.roadmap_feedback_count = sum(1 for row in candidates if row.requires_roadmap_feedback)
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save(
        update_fields=[
            'candidate_count',
            'ready_count',
            'blocked_count',
            'emitted_count',
            'duplicate_skipped_count',
            'memory_followup_count',
            'postmortem_followup_count',
            'roadmap_feedback_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {'run': run, 'candidates': candidates, 'recommendations': recommendations}
