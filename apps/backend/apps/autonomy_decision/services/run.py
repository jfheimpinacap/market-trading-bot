from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_decision.models import (
    DecisionRecommendation,
    DecisionRun,
    GovernanceDecision,
    GovernanceDecisionTargetScope,
)
from apps.autonomy_decision.services.candidates import build_decision_candidates
from apps.autonomy_decision.services.control import register_decision_for_proposal
from apps.autonomy_decision.services.recommendation import build_decision_recommendations


@transaction.atomic
def run_decision_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_decision_candidates()
    run = DecisionRun.objects.create(metadata={'actor': actor})
    ready_count = sum(1 for row in candidates if row.ready_for_decision)

    recommendations: list[DecisionRecommendation] = []
    registered = 0
    duplicate_skipped = 0

    for candidate in candidates:
        payload = candidate.__dict__
        for row in build_decision_recommendations(candidate=payload, ready_count=ready_count):
            recommendations.append(
                DecisionRecommendation.objects.create(
                    decision_run=run,
                    planning_proposal_id=candidate.planning_proposal,
                    decision_type=payload['metadata'].get('decision_type') or '',
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

        if candidate.ready_for_decision:
            decision = register_decision_for_proposal(proposal_id=candidate.planning_proposal, actor=actor)
            if decision.decision_status == 'DUPLICATE_SKIPPED':
                duplicate_skipped += 1
            else:
                registered += 1

    decisions = GovernanceDecision.objects.all()
    run.candidate_count = len(candidates)
    run.ready_count = ready_count
    run.blocked_count = sum(1 for row in candidates if row.blockers)
    run.registered_count = registered
    run.duplicate_skipped_count = duplicate_skipped
    run.roadmap_decision_count = decisions.filter(target_scope=GovernanceDecisionTargetScope.ROADMAP).count()
    run.scenario_decision_count = decisions.filter(target_scope=GovernanceDecisionTargetScope.SCENARIO).count()
    run.program_decision_count = decisions.filter(target_scope=GovernanceDecisionTargetScope.PROGRAM).count()
    run.manager_decision_count = decisions.filter(target_scope=GovernanceDecisionTargetScope.MANAGER).count()
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'recommendations': recommendations}
