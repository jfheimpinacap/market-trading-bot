from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_package.models import (
    GovernancePackage,
    GovernancePackageTargetScope,
    PackageRecommendation,
    PackageRun,
)
from apps.autonomy_package.services.candidates import build_package_candidates
from apps.autonomy_package.services.control import register_package_for_decision
from apps.autonomy_package.services.recommendation import build_package_recommendations


@transaction.atomic
def run_package_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_package_candidates()
    run = PackageRun.objects.create(metadata={'actor': actor})
    ready_count = sum(1 for row in candidates if row.ready_for_packaging)

    recommendations: list[PackageRecommendation] = []
    registered = 0
    duplicate_skipped = 0

    for candidate in candidates:
        payload = candidate.__dict__
        for row in build_package_recommendations(candidate=payload, ready_count=ready_count):
            recommendations.append(
                PackageRecommendation.objects.create(
                    package_run=run,
                    governance_decision_id=candidate.governance_decision,
                    package_type='',
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

        if candidate.ready_for_packaging:
            package = register_package_for_decision(decision_id=candidate.governance_decision, actor=actor)
            if package.package_status == 'DUPLICATE_SKIPPED':
                duplicate_skipped += 1
            else:
                registered += 1

    packages = GovernancePackage.objects.all()
    run.candidate_count = len(candidates)
    run.ready_count = ready_count
    run.blocked_count = sum(1 for row in candidates if row.blockers)
    run.registered_count = registered
    run.duplicate_skipped_count = duplicate_skipped
    run.roadmap_package_count = packages.filter(target_scope=GovernancePackageTargetScope.ROADMAP).count()
    run.scenario_package_count = packages.filter(target_scope=GovernancePackageTargetScope.SCENARIO).count()
    run.program_package_count = packages.filter(target_scope=GovernancePackageTargetScope.PROGRAM).count()
    run.manager_package_count = packages.filter(target_scope=GovernancePackageTargetScope.MANAGER).count()
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'recommendations': recommendations}
