from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.certification_board.models import (
    BaselineBindingResolutionStatus,
    BaselineConfirmationRecommendation,
    BaselineConfirmationRecommendationType,
    BaselineConfirmationRun,
    BaselineActivationCandidate,
    BaselineActivationRecommendation,
    BaselineActivationRecommendationType,
    BaselineActivationRun,
    PaperBaselineActivation,
    CertificationDecision,
    CertificationDecisionStatus,
    CertificationEvidenceSnapshot,
    CertificationLevel,
    CertificationRecommendation as CertificationRecommendationModel,
    CertificationRecommendationCode,
    CertificationRecommendationType,
    PaperBaselineConfirmation,
    PaperBaselineConfirmationStatus,
    RolloutCertificationRun,
)


@dataclass
class CertificationRecommendation:
    level: str
    code: str
    confidence: Decimal
    rationale: str
    reason_codes: list[str]
    blocking_constraints: list[str]
    remediation_items: list[str]
    evidence_summary: dict


def _d(value: str) -> Decimal:
    return Decimal(value)


def generate_recommendation(snapshot: CertificationEvidenceSnapshot) -> CertificationRecommendation:
    readiness = snapshot.readiness_summary or {}
    chaos = snapshot.chaos_benchmark_summary or {}
    incidents = snapshot.incident_summary or {}
    rollout = snapshot.rollout_summary or {}
    runtime_safety = snapshot.runtime_safety_summary or {}
    execution = snapshot.execution_evaluation_summary or {}
    champion = snapshot.champion_challenger_summary or {}

    reason_codes: list[str] = []
    blockers: list[str] = []
    remediation: list[str] = []

    readiness_status = readiness.get('status', 'UNKNOWN')
    chaos_score = float(chaos.get('latest_resilience_score') or 0)
    critical_incidents = int(incidents.get('open_critical') or 0)
    high_incidents = int(incidents.get('open_high') or 0)
    guardrail_critical = int(rollout.get('guardrail_critical_count') or 0)
    runtime_status = runtime_safety.get('runtime_status', 'UNKNOWN')
    safety_status = runtime_safety.get('safety_status', 'UNKNOWN')
    hard_stops = int(execution.get('hard_stop_count') or 0)
    favorable_rate = float(execution.get('favorable_review_rate') or 0)

    if readiness_status == 'NOT_READY':
        blockers.append('Readiness remains NOT_READY.')
        remediation.append('Resolve readiness critical gates before any certification increase.')
        reason_codes.append('READINESS_NOT_READY')

    if critical_incidents > 0:
        blockers.append('Critical incidents remain open.')
        remediation.append('Close or mitigate critical incidents with validated recovery.')
        reason_codes.append('OPEN_CRITICAL_INCIDENTS')

    if runtime_safety.get('kill_switch_enabled') or runtime_safety.get('hard_stop_active'):
        blockers.append('Safety kill switch or hard stop is active.')
        remediation.append('Clear safety hard-stop conditions and re-run evaluation.')
        reason_codes.append('SAFETY_HARD_STOP')

    if chaos_score and chaos_score < 45:
        blockers.append('Chaos resilience score is below conservative threshold.')
        remediation.append('Improve resilience benchmark results before recertification.')
        reason_codes.append('CHAOS_LOW_RESILIENCE')

    if guardrail_critical > 0:
        blockers.append('Critical rollout guardrail events detected recently.')
        remediation.append('Stabilize canary/rollout behavior before expanding autonomy.')
        reason_codes.append('ROLLOUT_CRITICAL_GUARDRAILS')

    if blockers:
        return CertificationRecommendation(
            level=CertificationLevel.REMEDIATION_REQUIRED if readiness_status == 'NOT_READY' or critical_incidents else CertificationLevel.NOT_CERTIFIED,
            code=CertificationRecommendationCode.REQUIRE_REMEDIATION,
            confidence=_d('0.92'),
            rationale='Critical blockers prevent paper autonomy certification uplift.',
            reason_codes=reason_codes,
            blocking_constraints=blockers,
            remediation_items=remediation,
            evidence_summary={
                'readiness_status': readiness_status,
                'chaos_score': chaos_score,
                'open_critical_incidents': critical_incidents,
                'open_high_incidents': high_incidents,
                'runtime_status': runtime_status,
                'safety_status': safety_status,
            },
        )

    if readiness_status == 'CAUTION' or high_incidents > 0 or hard_stops > 0 or favorable_rate < 0.55:
        return CertificationRecommendation(
            level=CertificationLevel.PAPER_CERTIFIED_DEFENSIVE,
            code=CertificationRecommendationCode.DOWNGRADE_TO_DEFENSIVE,
            confidence=_d('0.78'),
            rationale='Evidence is sufficient for paper operation, but requires defensive constraints.',
            reason_codes=['CAUTIONARY_EVIDENCE'],
            blocking_constraints=['No aggressive profile rollout while cautionary signals remain.'],
            remediation_items=['Increase favorable review rate and reduce high-severity incident backlog.'],
            evidence_summary={
                'readiness_status': readiness_status,
                'favorable_review_rate': favorable_rate,
                'open_high_incidents': high_incidents,
                'hard_stop_count': hard_stops,
            },
        )

    if (
        readiness_status == 'READY'
        and chaos_score >= 70
        and high_incidents == 0
        and guardrail_critical == 0
        and favorable_rate >= 0.62
        and champion.get('recommendation_code') in {'CHALLENGER_PROMISING', 'KEEP_CHAMPION'}
    ):
        high_conf = chaos_score >= 82 and favorable_rate >= 0.70
        return CertificationRecommendation(
            level=CertificationLevel.PAPER_CERTIFIED_HIGH_AUTONOMY if high_conf else CertificationLevel.PAPER_CERTIFIED_BALANCED,
            code=CertificationRecommendationCode.UPGRADE_PAPER_AUTONOMY if high_conf else CertificationRecommendationCode.HOLD_CURRENT_CERTIFICATION,
            confidence=_d('0.84') if high_conf else _d('0.74'),
            rationale='Readiness, resilience, incident control and execution evidence support controlled paper autonomy.',
            reason_codes=['EVIDENCE_SUFFICIENT_FOR_PAPER_AUTONOMY'],
            blocking_constraints=[],
            remediation_items=['Maintain stability window and re-run certification after major stack changes.'],
            evidence_summary={
                'readiness_status': readiness_status,
                'chaos_score': chaos_score,
                'favorable_review_rate': favorable_rate,
                'champion_signal': champion.get('recommendation_code'),
            },
        )

    return CertificationRecommendation(
        level=CertificationLevel.RECERTIFICATION_REQUIRED,
        code=CertificationRecommendationCode.MANUAL_REVIEW_REQUIRED,
        confidence=_d('0.60'),
        rationale='Evidence is inconclusive for automated certification changes; keep manual-first review.',
        reason_codes=['INCONCLUSIVE_EVIDENCE'],
        blocking_constraints=['Collect fresh readiness, chaos, and rollout evidence.'],
        remediation_items=['Run certification review again after updated evidence snapshots.'],
        evidence_summary={'readiness_status': readiness_status, 'chaos_score': chaos_score, 'favorable_review_rate': favorable_rate},
    )


def build_certification_recommendation(*, review_run: RolloutCertificationRun, decision: CertificationDecision) -> CertificationRecommendationModel:
    mapping = {
        CertificationDecisionStatus.CERTIFIED_FOR_PAPER_BASELINE: CertificationRecommendationType.CERTIFY_FOR_PAPER_BASELINE,
        CertificationDecisionStatus.KEEP_UNDER_OBSERVATION: CertificationRecommendationType.KEEP_UNDER_OBSERVATION,
        CertificationDecisionStatus.REQUIRE_MANUAL_REVIEW: CertificationRecommendationType.REQUIRE_MANUAL_CERTIFICATION_REVIEW,
        CertificationDecisionStatus.RECOMMEND_ROLLBACK: CertificationRecommendationType.RECOMMEND_MANUAL_ROLLBACK,
        CertificationDecisionStatus.REJECT_CERTIFICATION: CertificationRecommendationType.REJECT_CERTIFICATION,
    }
    recommendation_type = mapping[decision.decision_status]

    confidence = Decimal('0.60')
    if decision.decision_status == CertificationDecisionStatus.CERTIFIED_FOR_PAPER_BASELINE:
        confidence = Decimal('0.82')
    elif decision.decision_status == CertificationDecisionStatus.RECOMMEND_ROLLBACK:
        confidence = Decimal('0.88')
    elif decision.decision_status == CertificationDecisionStatus.REJECT_CERTIFICATION:
        confidence = Decimal('0.80')

    return CertificationRecommendationModel.objects.create(
        review_run=review_run,
        target_candidate=decision.linked_candidate,
        recommendation_type=recommendation_type,
        rationale=decision.rationale,
        reason_codes=decision.reason_codes,
        confidence=confidence,
        blockers=decision.blockers,
        metadata={
            'decision_id': decision.id,
            'decision_status': decision.decision_status,
        },
    )


def build_baseline_confirmation_recommendation(
    *, review_run: BaselineConfirmationRun, confirmation: PaperBaselineConfirmation
) -> BaselineConfirmationRecommendation:
    candidate = confirmation.linked_candidate

    if confirmation.confirmation_status == PaperBaselineConfirmationStatus.CONFIRMED:
        return BaselineConfirmationRecommendation.objects.create(
            review_run=review_run,
            target_confirmation=confirmation,
            recommendation_type=BaselineConfirmationRecommendationType.PREPARE_BASELINE_ROLLBACK,
            rationale='Confirmed baseline should keep an explicit rollback path to previous baseline.',
            reason_codes=['ROLLBACK_SHOULD_STAY_AVAILABLE'],
            confidence=Decimal('0.84'),
            blockers=[],
            metadata={'candidate_id': candidate.id},
        )

    if candidate.binding_resolution_status == BaselineBindingResolutionStatus.RESOLVED and candidate.ready_for_confirmation:
        return BaselineConfirmationRecommendation.objects.create(
            review_run=review_run,
            target_confirmation=confirmation,
            recommendation_type=BaselineConfirmationRecommendationType.CONFIRM_PAPER_BASELINE,
            rationale='Certified decision has resolved previous/proposed references and is safe for manual confirmation.',
            reason_codes=['CERTIFIED_AND_BINDINGS_RESOLVED'],
            confidence=Decimal('0.86'),
            blockers=[],
            metadata={'candidate_id': candidate.id},
        )

    if candidate.binding_resolution_status in {
        BaselineBindingResolutionStatus.BLOCKED,
        BaselineBindingResolutionStatus.PARTIAL,
    }:
        return BaselineConfirmationRecommendation.objects.create(
            review_run=review_run,
            target_confirmation=confirmation,
            recommendation_type=BaselineConfirmationRecommendationType.REQUIRE_BINDING_REVIEW,
            rationale='Certification is available but baseline binding mapping is incomplete for safe manual adoption.',
            reason_codes=['BINDING_MAPPING_INCOMPLETE'],
            confidence=Decimal('0.78'),
            blockers=candidate.blockers,
            metadata={'candidate_id': candidate.id},
        )

    return BaselineConfirmationRecommendation.objects.create(
        review_run=review_run,
        target_confirmation=confirmation,
        recommendation_type=BaselineConfirmationRecommendationType.DEFER_BASELINE_CONFIRMATION,
        rationale='Baseline confirmation should be deferred until the committee re-checks evidence and priority.',
        reason_codes=['DEFER_FOR_CONSERVATIVE_GOVERNANCE'],
        confidence=Decimal('0.62'),
        blockers=candidate.blockers,
        metadata={'candidate_id': candidate.id},
    )



def build_baseline_activation_recommendation(
    *, review_run: BaselineActivationRun, candidate: BaselineActivationCandidate, activation: PaperBaselineActivation
) -> BaselineActivationRecommendation:
    if activation.activation_status == 'ACTIVATED':
        return BaselineActivationRecommendation.objects.create(
            review_run=review_run,
            target_activation=activation,
            recommendation_type=BaselineActivationRecommendationType.PREPARE_ACTIVATION_ROLLBACK,
            rationale='Activation is manually applied; preserve explicit rollback readiness to previous active baseline.',
            reason_codes=['ACTIVATED_WITH_ROLLBACK_PATH'],
            confidence=Decimal('0.85'),
            blockers=[],
            metadata={'candidate_id': candidate.id, 'confirmation_id': candidate.linked_paper_baseline_confirmation_id},
        )

    if candidate.ready_for_activation and candidate.activation_resolution_status == BaselineBindingResolutionStatus.RESOLVED:
        return BaselineActivationRecommendation.objects.create(
            review_run=review_run,
            target_activation=activation,
            recommendation_type=BaselineActivationRecommendationType.ACTIVATE_PAPER_BASELINE,
            rationale='Confirmed baseline has resolved previous/proposed active references and is ready for manual activation.',
            reason_codes=['CONFIRMED_AND_READY_FOR_ACTIVATION'],
            confidence=Decimal('0.88'),
            blockers=[],
            metadata={'candidate_id': candidate.id, 'confirmation_id': candidate.linked_paper_baseline_confirmation_id},
        )

    if candidate.activation_resolution_status in {
        BaselineBindingResolutionStatus.BLOCKED,
        BaselineBindingResolutionStatus.PARTIAL,
    }:
        return BaselineActivationRecommendation.objects.create(
            review_run=review_run,
            target_activation=activation,
            recommendation_type=BaselineActivationRecommendationType.REQUIRE_BINDING_RECHECK,
            rationale='Activation mapping is incomplete; recheck champion/policy/trust/rollout bindings before manual apply.',
            reason_codes=['ACTIVATION_BINDING_MAPPING_INCOMPLETE'],
            confidence=Decimal('0.76'),
            blockers=candidate.blockers,
            metadata={'candidate_id': candidate.id, 'confirmation_id': candidate.linked_paper_baseline_confirmation_id},
        )

    return BaselineActivationRecommendation.objects.create(
        review_run=review_run,
        target_activation=activation,
        recommendation_type=BaselineActivationRecommendationType.DEFER_ACTIVATION,
        rationale='Defer activation until the committee re-checks priority and baseline context.',
        reason_codes=['DEFER_FOR_CONSERVATIVE_ACTIVATION_GOVERNANCE'],
        confidence=Decimal('0.62'),
        blockers=candidate.blockers,
        metadata={'candidate_id': candidate.id, 'confirmation_id': candidate.linked_paper_baseline_confirmation_id},
    )
