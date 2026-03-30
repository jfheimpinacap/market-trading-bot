from __future__ import annotations

from apps.experiment_lab.models import ExperimentCandidateReadinessStatus, ExperimentCandidateType
from apps.tuning_board.models import TuningProposal, TuningProposalStatus, TuningProposalType

PROPOSAL_TO_CANDIDATE_TYPE = {
    TuningProposalType.PREDICTION_CONFIDENCE_THRESHOLD: ExperimentCandidateType.THRESHOLD_CHALLENGER,
    TuningProposalType.PREDICTION_EDGE_THRESHOLD: ExperimentCandidateType.THRESHOLD_CHALLENGER,
    TuningProposalType.CALIBRATION_BIAS_OFFSET: ExperimentCandidateType.CALIBRATION_VARIANT,
    TuningProposalType.RISK_GATE_THRESHOLD: ExperimentCandidateType.RISK_GATE_VARIANT,
    TuningProposalType.RISK_SIZE_CAP: ExperimentCandidateType.SIZING_VARIANT,
    TuningProposalType.SHORTLIST_THRESHOLD: ExperimentCandidateType.SHORTLIST_VARIANT,
    TuningProposalType.OPPORTUNITY_CONVICTION_FLOOR: ExperimentCandidateType.OPPORTUNITY_VARIANT,
    TuningProposalType.LEARNING_CAUTION_WEIGHT: ExperimentCandidateType.LEARNING_WEIGHT_VARIANT,
}


HIGH_EVIDENCE_THRESHOLD = 0.6


def _resolve_readiness(proposal: TuningProposal) -> tuple[str, list[str]]:
    blockers = list(proposal.blockers or [])
    if proposal.proposal_status == TuningProposalStatus.DEFERRED:
        return ExperimentCandidateReadinessStatus.DEFERRED, blockers
    if proposal.proposal_status == TuningProposalStatus.WATCH:
        return ExperimentCandidateReadinessStatus.NEEDS_MORE_DATA, blockers + ['proposal in WATCH status']
    if proposal.evidence_strength_score < HIGH_EVIDENCE_THRESHOLD:
        return ExperimentCandidateReadinessStatus.NEEDS_MORE_DATA, blockers + ['low evidence strength']
    if proposal.proposal_status not in {TuningProposalStatus.READY_FOR_REVIEW, TuningProposalStatus.PROPOSED}:
        return ExperimentCandidateReadinessStatus.BLOCKED, blockers + [f'proposal status {proposal.proposal_status} is not eligible']
    return ExperimentCandidateReadinessStatus.READY, blockers


def build_candidate_specs(*, proposals: list[TuningProposal], proposal_to_bundle: dict[int, object]) -> list[dict]:
    specs: list[dict] = []
    for proposal in proposals:
        readiness, blockers = _resolve_readiness(proposal)
        specs.append(
            {
                'linked_tuning_proposal': proposal,
                'linked_tuning_bundle': proposal_to_bundle.get(proposal.id),
                'candidate_type': PROPOSAL_TO_CANDIDATE_TYPE.get(proposal.proposal_type, ExperimentCandidateType.THRESHOLD_CHALLENGER),
                'baseline_reference': 'champion_baseline',
                'challenger_label': f"challenger_tuning_{proposal.id}",
                'experiment_scope': proposal.target_scope,
                'readiness_status': readiness,
                'rationale': proposal.rationale,
                'blockers': blockers,
                'metadata': {
                    'target_component': proposal.target_component,
                    'proposal_type': proposal.proposal_type,
                    'source': 'tuning_board',
                },
            }
        )
    return specs
