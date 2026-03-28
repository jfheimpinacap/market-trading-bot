from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class RecommendationDraft:
    recommendation_code: str
    rationale: str
    reason_codes: list[str]
    supporting_evidence: list[dict]
    estimated_blockers: list[str]
    score: Decimal


def _score(risk) -> Decimal:
    return Decimal('1.0000') - (
        risk.dependency_conflict_risk * Decimal('0.32')
        + risk.approval_friction_risk * Decimal('0.18')
        + risk.degraded_posture_risk * Decimal('0.25')
        + risk.incident_exposure_risk * Decimal('0.15')
        + risk.rollback_likelihood_hint * Decimal('0.10')
    )


def build_recommendation_for_option(*, option, risk) -> RecommendationDraft:
    reason_codes: list[str] = []
    supporting = [{'option_type': option.option_type}, {'bundle_risk_level': risk.bundle_risk_level}]

    if risk.blockers:
        return RecommendationDraft(
            recommendation_code='DO_NOT_EXECUTE',
            rationale='Scenario is currently blocked by explicit dependencies or degraded posture signals.',
            reason_codes=['BLOCKED_BY_DEPENDENCY_OR_POSTURE', *risk.blockers[:2]],
            supporting_evidence=supporting,
            estimated_blockers=risk.blockers,
            score=Decimal('0.0500'),
        )

    if option.option_type == 'DELAY_UNTIL_STABLE':
        reason_codes.append('STABILIZATION_GUARDRAIL')
        return RecommendationDraft(
            recommendation_code='DELAY_UNTIL_STABLE',
            rationale='Delaying this promotion is healthier while stabilization evidence is incomplete.',
            reason_codes=reason_codes,
            supporting_evidence=supporting,
            estimated_blockers=risk.blockers,
            score=_score(risk),
        )

    if risk.approval_heavy:
        reason_codes.append('APPROVAL_FRICTION_HIGH')
        return RecommendationDraft(
            recommendation_code='REQUIRE_APPROVAL_HEAVY',
            rationale='Scenario is feasible but should be treated as approval-heavy with explicit operator gating.',
            reason_codes=reason_codes,
            supporting_evidence=supporting,
            estimated_blockers=risk.blockers,
            score=_score(risk) - Decimal('0.0500'),
        )

    if option.is_bundle and risk.bundle_risk_level == 'LOW':
        return RecommendationDraft(
            recommendation_code='SAFE_BUNDLE',
            rationale='Bundle is comparatively safe under current dependency and posture evidence.',
            reason_codes=['BUNDLE_LOW_RISK'],
            supporting_evidence=supporting,
            estimated_blockers=[],
            score=_score(risk),
        )

    if option.option_type == 'SEQUENCE_TWO_DOMAINS':
        return RecommendationDraft(
            recommendation_code='SEQUENCE_FIRST',
            rationale='Sequential progression lowers conflict and rollback risk versus parallel changes.',
            reason_codes=['SEQUENCE_REDUCES_CONFLICT'],
            supporting_evidence=supporting,
            estimated_blockers=[],
            score=_score(risk),
        )

    return RecommendationDraft(
        recommendation_code='BEST_NEXT_MOVE',
        rationale='Best next move under current evidence with conservative manual-first assumptions.',
        reason_codes=['LOWEST_COMPOSITE_RISK'],
        supporting_evidence=supporting,
        estimated_blockers=[],
        score=_score(risk),
    )
