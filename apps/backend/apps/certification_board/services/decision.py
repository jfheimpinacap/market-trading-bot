from __future__ import annotations

from apps.certification_board.models import (
    CertificationCandidate,
    CertificationDecision,
    CertificationDecisionStatus,
    CertificationEvidencePack,
    CertificationEvidenceStatus,
    StabilizationReadiness,
)
from apps.promotion_committee.models import PostRolloutStatusType


def build_certification_decision(*, candidate: CertificationCandidate, evidence_pack: CertificationEvidencePack) -> CertificationDecision:
    reason_codes: list[str] = []
    blockers = list(candidate.blockers or [])

    latest_status = candidate.linked_post_rollout_status.status if candidate.linked_post_rollout_status else None

    if candidate.stabilization_readiness == StabilizationReadiness.ROLLBACK_RECOMMENDED or latest_status in {
        PostRolloutStatusType.ROLLBACK_RECOMMENDED,
        PostRolloutStatusType.REVERTED,
    }:
        reason_codes.append('rollback_signal_detected')
        status = CertificationDecisionStatus.RECOMMEND_ROLLBACK
        rationale = 'Post-rollout safety signals indicate degradation. Manual rollback is recommended before baseline confirmation.'
    elif candidate.stabilization_readiness == StabilizationReadiness.BLOCKED:
        reason_codes.append('candidate_blocked')
        status = CertificationDecisionStatus.REJECT_CERTIFICATION
        rationale = 'Candidate is blocked and cannot be certified without manual remediation.'
    elif evidence_pack.evidence_status == CertificationEvidenceStatus.INSUFFICIENT:
        reason_codes.append('insufficient_evidence')
        status = CertificationDecisionStatus.KEEP_UNDER_OBSERVATION
        rationale = 'Evidence is insufficient; keep under observation before certification.'
    elif candidate.stabilization_readiness == StabilizationReadiness.REVIEW_REQUIRED:
        reason_codes.append('manual_review_required')
        status = CertificationDecisionStatus.REQUIRE_MANUAL_REVIEW
        rationale = 'Mixed post-rollout safety signals require manual certification review.'
    elif candidate.stabilization_readiness == StabilizationReadiness.NEEDS_OBSERVATION:
        reason_codes.append('extended_observation_required')
        status = CertificationDecisionStatus.KEEP_UNDER_OBSERVATION
        rationale = 'Candidate is not yet stable enough for certification; continue observation window.'
    elif candidate.target_scope == 'global' and evidence_pack.evidence_status != CertificationEvidenceStatus.STRONG:
        reason_codes.append('global_scope_requires_strong_evidence')
        status = CertificationDecisionStatus.REQUIRE_MANUAL_REVIEW
        rationale = 'Global-scope rollout requires stronger evidence or committee review before certification.'
    elif evidence_pack.evidence_status == CertificationEvidenceStatus.STRONG:
        reason_codes.append('strong_evidence_ready')
        status = CertificationDecisionStatus.CERTIFIED_FOR_PAPER_BASELINE
        rationale = 'Post-rollout evidence is strong and stability is sufficient for paper baseline certification.'
    elif evidence_pack.evidence_status in {CertificationEvidenceStatus.MIXED, CertificationEvidenceStatus.WEAK}:
        reason_codes.append('mixed_evidence_review')
        status = CertificationDecisionStatus.REQUIRE_MANUAL_REVIEW
        rationale = 'Evidence is mixed/weak and requires manual review before baseline confirmation.'
    else:
        reason_codes.append('default_observation_guardrail')
        status = CertificationDecisionStatus.KEEP_UNDER_OBSERVATION
        rationale = 'Default conservative path: keep under observation.'

    return CertificationDecision.objects.create(
        linked_candidate=candidate,
        linked_evidence_pack=evidence_pack,
        decision_status=status,
        rationale=rationale,
        reason_codes=reason_codes,
        blockers=blockers,
        metadata={
            'evidence_status': evidence_pack.evidence_status,
            'stabilization_readiness': candidate.stabilization_readiness,
            'manual_first': True,
            'paper_only': True,
        },
    )
