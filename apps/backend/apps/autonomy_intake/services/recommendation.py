from __future__ import annotations

from apps.autonomy_intake.models import IntakeRecommendationType, PlanningProposalType, PlanningTargetScope
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.autonomy_intake.services.candidates import IntakeCandidate

PROPOSAL_TYPE_BY_BACKLOG_TYPE = {
    'ROADMAP_CHANGE_CANDIDATE': PlanningProposalType.ROADMAP_PROPOSAL,
    'SCENARIO_CAUTION_CANDIDATE': PlanningProposalType.SCENARIO_PROPOSAL,
    'PROGRAM_GOVERNANCE_CANDIDATE': PlanningProposalType.PROGRAM_REVIEW_PROPOSAL,
    'MANAGER_REVIEW_ITEM': PlanningProposalType.MANAGER_REVIEW_PROPOSAL,
    'OPERATOR_REVIEW_ITEM': PlanningProposalType.OPERATOR_REVIEW_PROPOSAL,
}

TARGET_SCOPE_BY_PROPOSAL_TYPE = {
    PlanningProposalType.ROADMAP_PROPOSAL: PlanningTargetScope.ROADMAP,
    PlanningProposalType.SCENARIO_PROPOSAL: PlanningTargetScope.SCENARIO,
    PlanningProposalType.PROGRAM_REVIEW_PROPOSAL: PlanningTargetScope.PROGRAM,
    PlanningProposalType.MANAGER_REVIEW_PROPOSAL: PlanningTargetScope.MANAGER,
    PlanningProposalType.OPERATOR_REVIEW_PROPOSAL: PlanningTargetScope.OPERATOR_REVIEW,
}

RECOMMENDATION_BY_PROPOSAL_TYPE = {
    PlanningProposalType.ROADMAP_PROPOSAL: IntakeRecommendationType.EMIT_ROADMAP_PROPOSAL,
    PlanningProposalType.SCENARIO_PROPOSAL: IntakeRecommendationType.EMIT_SCENARIO_PROPOSAL,
    PlanningProposalType.PROGRAM_REVIEW_PROPOSAL: IntakeRecommendationType.EMIT_PROGRAM_REVIEW_PROPOSAL,
    PlanningProposalType.MANAGER_REVIEW_PROPOSAL: IntakeRecommendationType.EMIT_MANAGER_REVIEW_PROPOSAL,
    PlanningProposalType.OPERATOR_REVIEW_PROPOSAL: IntakeRecommendationType.EMIT_OPERATOR_REVIEW_PROPOSAL,
}


def proposal_type_for_backlog_type(backlog_type: str) -> str | None:
    return PROPOSAL_TYPE_BY_BACKLOG_TYPE.get(backlog_type)


def target_scope_for_proposal_type(proposal_type: str | None) -> str | None:
    if proposal_type is None:
        return None
    return TARGET_SCOPE_BY_PROPOSAL_TYPE[proposal_type]


def build_intake_recommendations(*, candidate: 'IntakeCandidate', has_duplicate: bool, queue_size: int) -> list[dict]:
    recommendations: list[dict] = []
    proposal_type = candidate.metadata.get('proposal_type')

    if candidate.blockers:
        recommendations.append(
            {
                'recommendation_type': IntakeRecommendationType.REQUIRE_MANUAL_INTAKE_REVIEW,
                'proposal_type': proposal_type or '',
                'rationale': 'Candidate requires manual intake review because mandatory readiness checks failed.',
                'reason_codes': ['candidate_blocked'],
                'confidence': '0.9200',
                'blockers': candidate.blockers,
                'metadata': {'backlog_item': candidate.backlog_item},
            }
        )
        return recommendations

    if has_duplicate:
        recommendations.append(
            {
                'recommendation_type': IntakeRecommendationType.SKIP_DUPLICATE_PROPOSAL,
                'proposal_type': proposal_type or '',
                'rationale': 'Matching intake proposal already exists for this backlog item and target scope.',
                'reason_codes': ['duplicate_planning_proposal'],
                'confidence': '0.9600',
                'blockers': [],
                'metadata': {'backlog_item': candidate.backlog_item},
            }
        )
    elif proposal_type:
        recommendations.append(
            {
                'recommendation_type': RECOMMENDATION_BY_PROPOSAL_TYPE[proposal_type],
                'proposal_type': proposal_type,
                'rationale': 'Backlog item is ready/prioritized and can be emitted as a governed planning proposal artifact.',
                'reason_codes': ['ready_for_planning_intake'],
                'confidence': '0.8600',
                'blockers': [],
                'metadata': {'backlog_item': candidate.backlog_item},
            }
        )

    if queue_size > 1:
        recommendations.append(
            {
                'recommendation_type': IntakeRecommendationType.REORDER_INTAKE_PRIORITY,
                'proposal_type': proposal_type or '',
                'rationale': f'{queue_size} ready intake items compete for the next planning cycle and should be reordered by explicit priority.',
                'reason_codes': ['queue_competition'],
                'confidence': '0.7700',
                'blockers': [],
                'metadata': {'ready_queue_size': queue_size},
            }
        )

    return recommendations
