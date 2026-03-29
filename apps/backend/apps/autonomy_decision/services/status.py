from apps.autonomy_decision.models import GovernanceDecisionTargetScope, GovernanceDecisionType
from apps.autonomy_intake.models import PlanningProposalType

DECISION_BY_PROPOSAL_TYPE = {
    PlanningProposalType.ROADMAP_PROPOSAL: GovernanceDecisionType.ROADMAP_DECISION_PACKAGE,
    PlanningProposalType.SCENARIO_PROPOSAL: GovernanceDecisionType.SCENARIO_DECISION_PACKAGE,
    PlanningProposalType.PROGRAM_REVIEW_PROPOSAL: GovernanceDecisionType.PROGRAM_DECISION_PACKAGE,
    PlanningProposalType.MANAGER_REVIEW_PROPOSAL: GovernanceDecisionType.MANAGER_DECISION_NOTE,
    PlanningProposalType.OPERATOR_REVIEW_PROPOSAL: GovernanceDecisionType.OPERATOR_DECISION_NOTE,
}

TARGET_BY_PROPOSAL_TYPE = {
    PlanningProposalType.ROADMAP_PROPOSAL: GovernanceDecisionTargetScope.ROADMAP,
    PlanningProposalType.SCENARIO_PROPOSAL: GovernanceDecisionTargetScope.SCENARIO,
    PlanningProposalType.PROGRAM_REVIEW_PROPOSAL: GovernanceDecisionTargetScope.PROGRAM,
    PlanningProposalType.MANAGER_REVIEW_PROPOSAL: GovernanceDecisionTargetScope.MANAGER,
    PlanningProposalType.OPERATOR_REVIEW_PROPOSAL: GovernanceDecisionTargetScope.OPERATOR_REVIEW,
}
