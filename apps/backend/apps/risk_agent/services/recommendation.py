from __future__ import annotations

from decimal import Decimal

from apps.risk_agent.models import (
    PositionWatchPlan,
    RiskApprovalDecision,
    RiskRuntimeApprovalStatus,
    RiskRuntimeRecommendation,
    RiskRuntimeRecommendationType,
    RiskRuntimeRun,
)


def build_runtime_recommendations(*, runtime_run: RiskRuntimeRun, candidate, approval_decision: RiskApprovalDecision, watch_plan: PositionWatchPlan) -> list[RiskRuntimeRecommendation]:
    recommendations: list[RiskRuntimeRecommendation] = []

    if approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED:
        recommendations.append(
            RiskRuntimeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_candidate=candidate,
                recommendation_type=RiskRuntimeRecommendationType.APPROVE_FOR_PAPER_EXECUTION,
                rationale='Risk posture is acceptable for conservative paper execution.',
                reason_codes=['APPROVED_BASELINE'],
                confidence=Decimal('0.7800'),
                blockers=[],
                metadata={'manual_apply_required': True},
            )
        )
        recommendations.append(
            RiskRuntimeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_candidate=candidate,
                recommendation_type=RiskRuntimeRecommendationType.SEND_TO_EXECUTION_SIMULATOR,
                rationale='Approved paper candidate can be forwarded to simulator only.',
                reason_codes=['PAPER_ONLY_HANDOFF'],
                confidence=Decimal('0.7600'),
                blockers=[],
                metadata={'execution_simulator_only': True},
            )
        )
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
        recommendations.append(
            RiskRuntimeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_candidate=candidate,
                recommendation_type=RiskRuntimeRecommendationType.APPROVE_REDUCED_SIZE,
                rationale='Candidate accepted with conservative reduced size and strict watch.',
                reason_codes=approval_decision.reason_codes,
                confidence=Decimal('0.6600'),
                blockers=approval_decision.blockers,
                metadata={'manual_apply_required': True},
            )
        )
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.BLOCKED:
        recommendation_type = RiskRuntimeRecommendationType.BLOCK_HIGH_RISK
        if 'LOW_CONFIDENCE' in (approval_decision.blockers or []):
            recommendation_type = RiskRuntimeRecommendationType.BLOCK_LOW_CONFIDENCE
        if 'POOR_LIQUIDITY' in (approval_decision.blockers or []):
            recommendation_type = RiskRuntimeRecommendationType.BLOCK_POOR_LIQUIDITY

        recommendations.append(
            RiskRuntimeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_candidate=candidate,
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
            RiskRuntimeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_candidate=candidate,
                recommendation_type=RiskRuntimeRecommendationType.REQUIRE_MANUAL_RISK_REVIEW,
                rationale='Borderline evidence profile requires manual operator risk review.',
                reason_codes=approval_decision.reason_codes,
                confidence=Decimal('0.6100'),
                blockers=approval_decision.blockers,
                metadata={'manual_review_only': True},
            )
        )

    if watch_plan.watch_status != 'NOT_NEEDED':
        recommendations.append(
            RiskRuntimeRecommendation.objects.create(
                runtime_run=runtime_run,
                target_candidate=candidate,
                recommendation_type=RiskRuntimeRecommendationType.KEEP_ON_WATCH,
                rationale='Attach post-entry watch plan to preserve conservative operation.',
                reason_codes=['WATCH_REQUIRED'],
                confidence=Decimal('0.7000'),
                blockers=[],
                metadata={'position_manager_handoff': True},
            )
        )

    return recommendations
