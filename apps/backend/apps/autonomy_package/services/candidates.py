from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_decision.models import GovernanceDecision, GovernanceDecisionStatus
from apps.autonomy_package.models import GovernancePackageTargetScope
from apps.autonomy_package.services.dedup import find_duplicate_package


@dataclass
class PackageCandidate:
    governance_decision: int
    planning_proposal: int | None
    backlog_item: int | None
    insight: int | None
    campaign: int | None
    decision_type: str
    target_scope: str
    priority_level: str
    ready_for_packaging: bool
    grouping_key: str
    existing_package: int | None
    blockers: list[str]
    metadata: dict


def build_package_candidates() -> list[PackageCandidate]:
    rows: list[PackageCandidate] = []
    decisions = GovernanceDecision.objects.select_related('planning_proposal', 'campaign').filter(
        decision_status__in=[GovernanceDecisionStatus.REGISTERED, GovernanceDecisionStatus.ACKNOWLEDGED],
    ).order_by('-updated_at', '-id')[:500]

    for decision in decisions:
        proposal_type = decision.planning_proposal.proposal_type if decision.planning_proposal else 'cross'
        grouping_key = f"{decision.target_scope}:{proposal_type}:{decision.priority_level}"
        duplicate = find_duplicate_package(grouping_key=grouping_key, target_scope=decision.target_scope)

        blockers = list(decision.blockers or [])
        if decision.decision_status not in [GovernanceDecisionStatus.REGISTERED, GovernanceDecisionStatus.ACKNOWLEDGED]:
            blockers.append('decision_not_registered')
        if decision.target_scope not in GovernancePackageTargetScope.values:
            blockers.append('unsupported_target_scope')

        rows.append(
            PackageCandidate(
                governance_decision=decision.id,
                planning_proposal=decision.planning_proposal_id,
                backlog_item=decision.backlog_item_id,
                insight=decision.insight_id,
                campaign=decision.campaign_id,
                decision_type=decision.decision_type,
                target_scope=decision.target_scope,
                priority_level=decision.priority_level,
                ready_for_packaging=not blockers and duplicate is None,
                grouping_key=grouping_key,
                existing_package=duplicate.id if duplicate else None,
                blockers=blockers,
                metadata={'decision_status': decision.decision_status, 'campaign_title': decision.campaign.title if decision.campaign else None},
            )
        )

    return rows
