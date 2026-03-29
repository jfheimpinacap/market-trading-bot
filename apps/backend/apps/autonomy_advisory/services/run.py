from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_advisory.models import AdvisoryArtifactStatus, AdvisoryRecommendation, AdvisoryRun
from .candidates import build_advisory_candidates
from .control import emit_advisory_for_insight
from .recommendation import recommendation_for_candidate


@transaction.atomic
def run_advisory_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_advisory_candidates()
    run = AdvisoryRun.objects.create(metadata={'actor': actor})

    recommendations = []
    for candidate in candidates:
        row = recommendation_for_candidate(candidate)
        recommendations.append(
            AdvisoryRecommendation.objects.create(
                advisory_run=run,
                campaign_insight_id=candidate.insight_id,
                target_campaign_id=candidate.campaign_id,
                recommendation_type=row['recommendation_type'],
                artifact_type=row['artifact_type'],
                rationale=row['rationale'],
                reason_codes=row['reason_codes'],
                confidence=row['confidence'],
                blockers=row['blockers'],
                metadata=row['metadata'],
            )
        )

    ready_candidates = [candidate for candidate in candidates if candidate.ready_for_emission]
    if len(ready_candidates) > 1:
        AdvisoryRecommendation.objects.create(
            advisory_run=run,
            recommendation_type='REORDER_ADVISORY_PRIORITY',
            rationale='Multiple advisory candidates are ready; prioritize manually by campaign urgency.',
            reason_codes=['multiple_ready_candidates'],
            confidence='0.7000',
            blockers=[],
            metadata={'ready_candidates': [candidate.insight_id for candidate in ready_candidates]},
        )

    emitted_artifacts = [emit_advisory_for_insight(insight_id=candidate.insight_id, actor=actor, advisory_run=run) for candidate in ready_candidates]

    run.candidate_count = len(candidates)
    run.ready_count = len(ready_candidates)
    run.blocked_count = sum(1 for candidate in candidates if not candidate.ready_for_emission)
    run.emitted_count = sum(1 for artifact in emitted_artifacts if artifact.artifact_status == AdvisoryArtifactStatus.EMITTED)
    run.duplicate_skipped_count = sum(1 for artifact in emitted_artifacts if artifact.artifact_status == AdvisoryArtifactStatus.DUPLICATE_SKIPPED)
    run.memory_note_count = sum(1 for artifact in emitted_artifacts if artifact.artifact_type == 'MEMORY_PRECEDENT_NOTE')
    run.roadmap_note_count = sum(1 for artifact in emitted_artifacts if artifact.artifact_type == 'ROADMAP_GOVERNANCE_NOTE')
    run.scenario_note_count = sum(1 for artifact in emitted_artifacts if artifact.artifact_type == 'SCENARIO_CAUTION_NOTE')
    run.program_note_count = sum(1 for artifact in emitted_artifacts if artifact.artifact_type == 'PROGRAM_POLICY_NOTE')
    run.manager_note_count = sum(1 for artifact in emitted_artifacts if artifact.artifact_type == 'MANAGER_REVIEW_NOTE')
    run.recommendation_summary = dict(Counter(rec.recommendation_type for rec in AdvisoryRecommendation.objects.filter(advisory_run=run)))
    run.save()

    return {
        'run': run,
        'candidates': candidates,
        'recommendations': recommendations,
        'emitted_artifacts': emitted_artifacts,
    }
