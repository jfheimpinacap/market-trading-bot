from __future__ import annotations

from decimal import Decimal

from apps.risk_agent.models import (
    AutonomousExecutionReadiness,
    PositionWatchPlan,
    RiskIntakeRecommendation,
    RiskIntakeRecommendationType,
    RiskApprovalDecision,
    RiskRuntimeApprovalStatus,
    RiskRuntimeRun,
)


def build_runtime_recommendations(
    *,
    runtime_run: RiskRuntimeRun,
    candidate,
    approval_decision: RiskApprovalDecision,
    watch_plan: PositionWatchPlan,
    readiness: AutonomousExecutionReadiness,
) -> list[RiskIntakeRecommendation]:
    recommendations: list[RiskIntakeRecommendation] = []

    if approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED:
        recommendations.append(
            RiskIntakeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_market=candidate.linked_market,
                target_intake_candidate=candidate,
                target_approval_review=approval_decision,
                target_readiness=readiness,
                recommendation_type=RiskIntakeRecommendationType.APPROVE_FOR_AUTONOMOUS_EXECUTION,
                rationale='Risk posture is acceptable for conservative autonomous paper execution.',
                reason_codes=['APPROVED_BASELINE'],
                confidence=Decimal('0.7800'),
                blockers=[],
                metadata={'manual_apply_required': True},
            )
        )
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
        recommendations.append(
            RiskIntakeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_market=candidate.linked_market,
                target_intake_candidate=candidate,
                target_approval_review=approval_decision,
                target_readiness=readiness,
                recommendation_type=RiskIntakeRecommendationType.APPROVE_WITH_REDUCED_SIZE,
                rationale='Candidate accepted with conservative reduced size and strict watch.',
                reason_codes=approval_decision.reason_codes,
                confidence=Decimal('0.6600'),
                blockers=approval_decision.blockers,
                metadata={'manual_apply_required': True},
            )
        )
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.BLOCKED:
        recommendation_type = RiskIntakeRecommendationType.BLOCK_FOR_RISK_POSTURE
        if 'PORTFOLIO_PRESSURE_HIGH' in (candidate.reason_codes or []):
            recommendation_type = RiskIntakeRecommendationType.BLOCK_FOR_PORTFOLIO_PRESSURE

        recommendations.append(
            RiskIntakeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_market=candidate.linked_market,
                target_intake_candidate=candidate,
                target_approval_review=approval_decision,
                target_readiness=readiness,
                recommendation_type=recommendation_type,
                rationale='Candidate blocked by explicit risk gate rules.',
                reason_codes=approval_decision.reason_codes,
                confidence=Decimal('0.8200'),
                blockers=approval_decision.blockers,
                metadata={'manual_review_reentry_required': True},
            )
        )
    else:
        recommendations.append(
            RiskIntakeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_market=candidate.linked_market,
                target_intake_candidate=candidate,
                target_approval_review=approval_decision,
                target_readiness=readiness,
                recommendation_type=RiskIntakeRecommendationType.REQUIRE_MANUAL_RISK_REVIEW,
                rationale='Borderline evidence profile requires manual operator risk review.',
                reason_codes=approval_decision.reason_codes,
                confidence=Decimal('0.6100'),
                blockers=approval_decision.blockers,
                metadata={'manual_review_only': True},
            )
        )

    if watch_plan.watch_status != 'NOT_NEEDED':
        recommendations.append(
            RiskIntakeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_market=candidate.linked_market,
                target_intake_candidate=candidate,
                target_approval_review=approval_decision,
                target_readiness=readiness,
                recommendation_type=RiskIntakeRecommendationType.KEEP_ON_WATCH_ONLY,
                rationale='Attach post-entry watch plan to preserve conservative operation.',
                reason_codes=['WATCH_REQUIRED'],
                confidence=Decimal('0.7000'),
                blockers=[],
                metadata={'position_manager_handoff': True},
            )
        )

    return recommendations
