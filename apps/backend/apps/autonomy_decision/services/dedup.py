from apps.autonomy_decision.models import GovernanceDecision


def find_duplicate_decision(*, proposal_id: int, target_scope: str) -> GovernanceDecision | None:
    return GovernanceDecision.objects.filter(
        planning_proposal_id=proposal_id,
        target_scope=target_scope,
        decision_status__in=['REGISTERED', 'ACKNOWLEDGED', 'READY'],
    ).first()
