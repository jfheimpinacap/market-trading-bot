from __future__ import annotations

from apps.portfolio_governor.models import (
    PortfolioExposureApplyDecision,
    PortfolioExposureApplyDecisionStatus,
    PortfolioExposureApplyRun,
    PortfolioExposureApplyTarget,
    PortfolioExposureApplyType,
    PortfolioExposureDecision,
    PortfolioExposureDecisionType,
)
from apps.runtime_governor.mode_enforcement.services.enforcement import get_module_enforcement_state

APPLY_TYPE_BY_DECISION = {
    PortfolioExposureDecisionType.THROTTLE_NEW_ENTRIES: PortfolioExposureApplyType.APPLY_THROTTLE_NEW_ENTRIES,
    PortfolioExposureDecisionType.DEFER_PENDING_DISPATCH: PortfolioExposureApplyType.APPLY_DEFER_PENDING_DISPATCH,
    PortfolioExposureDecisionType.PARK_WEAKER_SESSION: PortfolioExposureApplyType.APPLY_PARK_SESSION,
    PortfolioExposureDecisionType.PAUSE_CLUSTER_ACTIVITY: PortfolioExposureApplyType.APPLY_PAUSE_CLUSTER_ACTIVITY,
    PortfolioExposureDecisionType.REQUIRE_MANUAL_EXPOSURE_REVIEW: PortfolioExposureApplyType.APPLY_MANUAL_REVIEW_ONLY,
    PortfolioExposureDecisionType.KEEP_EXPOSURE_AS_IS: PortfolioExposureApplyType.APPLY_NO_CHANGE,
}


def derive_apply_decision(
    *,
    apply_run: PortfolioExposureApplyRun,
    decision: PortfolioExposureDecision,
    targets: list[PortfolioExposureApplyTarget],
    resolver_reason_codes: list[str],
) -> PortfolioExposureApplyDecision:
    apply_type = APPLY_TYPE_BY_DECISION.get(decision.decision_type, PortfolioExposureApplyType.APPLY_MANUAL_REVIEW_ONLY)
    status = PortfolioExposureApplyDecisionStatus.PROPOSED
    auto_applicable = bool(decision.auto_applicable)
    reason_codes = list(decision.reason_codes or []) + list(resolver_reason_codes)
    summary = f'Apply bridge derived {apply_type} from exposure decision #{decision.id}.'

    if apply_type in [PortfolioExposureApplyType.APPLY_MANUAL_REVIEW_ONLY, PortfolioExposureApplyType.APPLY_NO_CHANGE]:
        auto_applicable = False

    if apply_type == PortfolioExposureApplyType.APPLY_DEFER_PENDING_DISPATCH and not any(
        t.target_type == 'PENDING_DISPATCH' for t in targets
    ):
        status = PortfolioExposureApplyDecisionStatus.BLOCKED
        auto_applicable = False
        reason_codes.append('missing_pending_dispatch_targets')
        summary = 'No pending dispatch targets were found; defer apply is blocked.'

    if apply_type in [PortfolioExposureApplyType.APPLY_PARK_SESSION, PortfolioExposureApplyType.APPLY_PAUSE_CLUSTER_ACTIVITY] and not any(
        t.target_type == 'SESSION' for t in targets
    ):
        status = PortfolioExposureApplyDecisionStatus.BLOCKED
        auto_applicable = False
        reason_codes.append('missing_session_targets')
        summary = 'No runtime sessions were found for conservative park/pause apply.'

    apply_enforcement = get_module_enforcement_state(module_name='exposure_apply')
    apply_impact = (apply_enforcement.get('impact') or {}).get('impact_status')
    if apply_impact == 'REDUCED':
        auto_applicable = False
        reason_codes.append('global_mode_enforcement_manual_review_bias')
        if status == PortfolioExposureApplyDecisionStatus.PROPOSED:
            status = PortfolioExposureApplyDecisionStatus.BLOCKED
        summary = 'Global mode enforcement requires manual review bias before applying new exposure.'
    elif apply_impact == 'THROTTLED':
        if apply_type in [PortfolioExposureApplyType.APPLY_THROTTLE_NEW_ENTRIES, PortfolioExposureApplyType.APPLY_DEFER_PENDING_DISPATCH]:
            reason_codes.append('global_mode_enforcement_throttle_apply')
        else:
            auto_applicable = False
            reason_codes.append('global_mode_enforcement_apply_throttled')
    elif apply_impact in {'MONITOR_ONLY', 'BLOCKED'}:
        auto_applicable = False
        status = PortfolioExposureApplyDecisionStatus.BLOCKED
        reason_codes.append('global_mode_enforcement_block_apply')
        summary = 'Global mode enforcement blocked autonomous exposure apply.'

    return PortfolioExposureApplyDecision.objects.create(
        linked_apply_run=apply_run,
        linked_exposure_decision=decision,
        apply_type=apply_type,
        apply_status=status,
        auto_applicable=auto_applicable,
        apply_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'paper_only': True,
            'local_first': True,
            'no_live_execution': True,
            'no_aggressive_position_closing': True,
            'mode_enforcement': apply_enforcement,
        },
    )
