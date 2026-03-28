from __future__ import annotations

from decimal import Decimal

from apps.autonomy_manager.models import (
    AutonomyRecommendationCode,
    AutonomyStage,
    AutonomyStageRecommendation,
    AutonomyStageState,
)
from apps.autonomy_manager.services.evidence import DomainEvidence


def _promote_stage(stage: str) -> str:
    if stage == AutonomyStage.MANUAL:
        return AutonomyStage.ASSISTED
    if stage == AutonomyStage.ASSISTED:
        return AutonomyStage.SUPERVISED_AUTOPILOT
    return stage


def _decide_code(*, stage: str, evidence: DomainEvidence) -> tuple[str, str, list[str], Decimal, str]:
    reasons: list[str] = []

    if evidence.sample_size < 2 or evidence.trust_require_more_data > 0:
        reasons.append('INSUFFICIENT_DOMAIN_DATA')
        return (
            AutonomyRecommendationCode.REQUIRE_MORE_DATA,
            stage,
            reasons,
            Decimal('0.4500'),
            'Not enough domain evidence yet; keep stage and gather more observations.',
        )

    if evidence.incidents_high > 0:
        reasons.append('ACTIVE_HIGH_INCIDENTS')
    if evidence.rollout_rollback_recommended > 0:
        reasons.append('ROLLBACK_RECOMMENDED_SIGNAL')
    if evidence.certification_constrained:
        reasons.append('CERTIFICATION_CONSTRAINED')

    if reasons:
        if stage == AutonomyStage.SUPERVISED_AUTOPILOT:
            return (
                AutonomyRecommendationCode.ROLLBACK_STAGE,
                AutonomyStage.ASSISTED,
                reasons,
                Decimal('0.8300'),
                'Risk signals indicate supervised autopilot should roll back to assisted.',
            )
        if stage in {AutonomyStage.ASSISTED, AutonomyStage.MANUAL}:
            return (
                AutonomyRecommendationCode.FREEZE_DOMAIN,
                AutonomyStage.FROZEN,
                reasons,
                Decimal('0.8200'),
                'Domain should be frozen while incidents/rollback signals are active.',
            )

    if evidence.trust_downgrade > evidence.trust_promote:
        return (
            AutonomyRecommendationCode.DOWNGRADE_TO_MANUAL,
            AutonomyStage.MANUAL,
            ['TRUST_DOWNGRADE_DOMINANT'],
            Decimal('0.7400'),
            'Trust calibration indicates conservative downgrade to manual.',
        )

    if evidence.trust_promote > 0 and evidence.auto_success_rate >= 0.85:
        proposed = _promote_stage(stage)
        if proposed != stage:
            return (
                AutonomyRecommendationCode.PROMOTE_TO_SUPERVISED_AUTOPILOT if proposed == AutonomyStage.SUPERVISED_AUTOPILOT else AutonomyRecommendationCode.PROMOTE_TO_ASSISTED,
                proposed,
                ['PROMOTION_SIGNALS_STABLE'],
                Decimal('0.7800'),
                'Promotion signals are stable with strong success-rate support.',
            )

    return (
        AutonomyRecommendationCode.KEEP_CURRENT_STAGE,
        stage,
        ['STAGE_STABLE'],
        Decimal('0.6200'),
        'Current domain stage remains appropriate for current evidence.',
    )


def create_recommendation(*, state: AutonomyStageState, evidence: DomainEvidence) -> AutonomyStageRecommendation:
    code, proposed_stage, reason_codes, confidence, rationale = _decide_code(stage=state.current_stage, evidence=evidence)

    return AutonomyStageRecommendation.objects.create(
        domain=state.domain,
        state=state,
        recommendation_code=code,
        current_stage=state.current_stage,
        proposed_stage=proposed_stage,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=confidence,
        evidence_refs=evidence.evidence_refs,
        metadata={
            'sample_size': evidence.sample_size,
            'trust_promote': evidence.trust_promote,
            'trust_downgrade': evidence.trust_downgrade,
            'rollout_rollback_recommended': evidence.rollout_rollback_recommended,
            'incidents_high': evidence.incidents_high,
            'approval_friction_pending': evidence.approvals_pending,
            'rollback_history': evidence.rollback_history,
            'auto_success_rate': f'{evidence.auto_success_rate:.4f}',
        },
    )
