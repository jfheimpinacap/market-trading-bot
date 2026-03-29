from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_seed.models import GovernanceSeed, SeedRecommendation, SeedRun
from apps.autonomy_seed.services.candidates import build_seed_candidates
from apps.autonomy_seed.services.control import register_seed_for_package
from apps.autonomy_seed.services.recommendation import build_seed_recommendations


@transaction.atomic
def run_seed_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_seed_candidates()
    run = SeedRun.objects.create(metadata={'actor': actor})
    ready_count = sum(1 for row in candidates if row.ready_for_seed)

    recommendations: list[SeedRecommendation] = []
    registered = 0
    duplicate_skipped = 0

    for candidate in candidates:
        payload = candidate.__dict__
        for row in build_seed_recommendations(candidate=payload, ready_count=ready_count):
            recommendations.append(
                SeedRecommendation.objects.create(
                    seed_run=run,
                    governance_package_id=candidate.governance_package,
                    recommendation_type=row['recommendation_type'],
                    seed_type=row['seed_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

        if candidate.ready_for_seed:
            seed = register_seed_for_package(package_id=candidate.governance_package, actor=actor)
            if seed.seed_status == 'DUPLICATE_SKIPPED':
                duplicate_skipped += 1
            else:
                registered += 1

    seeds = GovernanceSeed.objects.all()
    run.candidate_count = len(candidates)
    run.ready_count = ready_count
    run.blocked_count = sum(1 for row in candidates if row.blockers)
    run.registered_count = registered
    run.duplicate_skipped_count = duplicate_skipped
    run.roadmap_seed_count = seeds.filter(target_scope='roadmap').count()
    run.scenario_seed_count = seeds.filter(target_scope='scenario').count()
    run.program_seed_count = seeds.filter(target_scope='program').count()
    run.manager_seed_count = seeds.filter(target_scope='manager').count()
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'recommendations': recommendations}
