from __future__ import annotations

from dataclasses import dataclass, field

from apps.mission_control.models import (
    AutonomousResumeDecision,
    AutonomousSessionAdmissionDecision,
    AutonomousSessionInterventionDecision,
    GovernanceReviewSourceModule,
    GovernanceReviewSourceType,
)
from apps.portfolio_governor.models import PortfolioExposureApplyDecision, PortfolioExposureDecision
from apps.runtime_governor.models import RuntimeFeedbackApplyDecision, RuntimeModeTransitionDecision


@dataclass
class CollectedGovernanceItem:
    source_module: str
    source_type: str
    source_object_id: int
    title: str
    summary: str
    reason_codes: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    linked_session_id: int | None = None
    linked_market_id: int | None = None


def _extract_reason_codes(value: list[str] | None) -> list[str]:
    return [code for code in (value or []) if isinstance(code, str)]


def _make_blockers_from_status(status: str, reason_codes: list[str], decision_type: str) -> list[str]:
    blockers: list[str] = []
    status_value = (status or '').upper()
    if status_value == 'BLOCKED':
        blockers.append('STATUS_BLOCKED')
    if 'DEFER' in (decision_type or ''):
        blockers.append('DEFERRED_DECISION')
    blockers.extend([reason for reason in reason_codes if any(token in reason.upper() for token in ('BLOCK', 'SAFETY', 'INCIDENT', 'RUNTIME'))])
    return list(dict.fromkeys(blockers))


def _include_item(status: str, decision_type: str, blockers: list[str]) -> bool:
    status_upper = (status or '').upper()
    if status_upper in {'APPLIED'}:
        return False
    if status_upper in {'BLOCKED', 'PROPOSED', 'SKIPPED'}:
        return True
    if blockers:
        return True
    return any(flag in (decision_type or '') for flag in ('MANUAL', 'DEFER', 'BLOCK', 'ADVISORY'))


def collect_governance_review_candidates() -> list[CollectedGovernanceItem]:
    items: list[CollectedGovernanceItem] = []

    for decision in RuntimeFeedbackApplyDecision.objects.select_related('linked_feedback_decision').order_by('-created_at')[:200]:
        reason_codes = _extract_reason_codes(decision.reason_codes)
        blockers = _make_blockers_from_status(decision.apply_status, reason_codes, decision.apply_type)
        if not _include_item(decision.apply_status, decision.apply_type, blockers):
            continue
        items.append(CollectedGovernanceItem(
            source_module=GovernanceReviewSourceModule.RUNTIME_GOVERNOR,
            source_type=GovernanceReviewSourceType.MODE_FEEDBACK_APPLY,
            source_object_id=decision.id,
            title=f'Runtime feedback apply: {decision.apply_type}',
            summary=decision.apply_summary or 'Runtime feedback apply decision pending governance review.',
            reason_codes=reason_codes,
            blockers=blockers,
            metadata={'apply_status': decision.apply_status, 'auto_applicable': decision.auto_applicable},
        ))

    for decision in RuntimeModeTransitionDecision.objects.select_related('linked_transition_snapshot').order_by('-created_at')[:200]:
        reason_codes = _extract_reason_codes(decision.reason_codes)
        blockers = _make_blockers_from_status(decision.decision_status, reason_codes, decision.decision_type)
        if not _include_item(decision.decision_status, decision.decision_type, blockers):
            continue
        items.append(CollectedGovernanceItem(
            source_module=GovernanceReviewSourceModule.RUNTIME_GOVERNOR,
            source_type=GovernanceReviewSourceType.MODE_STABILIZATION,
            source_object_id=decision.id,
            title=f'Mode stabilization: {decision.decision_type}',
            summary=decision.decision_summary or 'Runtime mode stabilization decision pending governance review.',
            reason_codes=reason_codes,
            blockers=blockers,
            metadata={'decision_status': decision.decision_status, 'auto_applicable': decision.auto_applicable},
        ))

    for decision in AutonomousSessionInterventionDecision.objects.select_related('linked_session').order_by('-created_at')[:200]:
        reason_codes = _extract_reason_codes(decision.reason_codes)
        blockers = _make_blockers_from_status(decision.decision_status, reason_codes, decision.decision_type)
        if not _include_item(decision.decision_status, decision.decision_type, blockers):
            continue
        items.append(CollectedGovernanceItem(
            source_module=GovernanceReviewSourceModule.MISSION_CONTROL,
            source_type=GovernanceReviewSourceType.SESSION_HEALTH,
            source_object_id=decision.id,
            linked_session_id=decision.linked_session_id,
            title=f'Session health: {decision.decision_type}',
            summary=decision.decision_summary or 'Session health decision pending governance review.',
            reason_codes=reason_codes,
            blockers=blockers,
            metadata={'decision_status': decision.decision_status, 'auto_applicable': decision.auto_applicable},
        ))

    for decision in AutonomousResumeDecision.objects.select_related('linked_session').order_by('-created_at')[:200]:
        reason_codes = _extract_reason_codes(decision.reason_codes)
        blockers = _make_blockers_from_status(decision.decision_status, reason_codes, decision.decision_type)
        if not _include_item(decision.decision_status, decision.decision_type, blockers):
            continue
        items.append(CollectedGovernanceItem(
            source_module=GovernanceReviewSourceModule.MISSION_CONTROL,
            source_type=GovernanceReviewSourceType.SESSION_RECOVERY,
            source_object_id=decision.id,
            linked_session_id=decision.linked_session_id,
            title=f'Session recovery: {decision.decision_type}',
            summary=decision.decision_summary or 'Session recovery decision pending governance review.',
            reason_codes=reason_codes,
            blockers=blockers,
            metadata={'decision_status': decision.decision_status, 'auto_applicable': decision.auto_applicable},
        ))

    for decision in AutonomousSessionAdmissionDecision.objects.select_related('linked_session').order_by('-created_at')[:200]:
        reason_codes = _extract_reason_codes(decision.reason_codes)
        blockers = _make_blockers_from_status(decision.decision_status, reason_codes, decision.decision_type)
        if not _include_item(decision.decision_status, decision.decision_type, blockers):
            continue
        items.append(CollectedGovernanceItem(
            source_module=GovernanceReviewSourceModule.MISSION_CONTROL,
            source_type=GovernanceReviewSourceType.SESSION_ADMISSION,
            source_object_id=decision.id,
            linked_session_id=decision.linked_session_id,
            title=f'Session admission: {decision.decision_type}',
            summary=decision.decision_summary or 'Session admission decision pending governance review.',
            reason_codes=reason_codes,
            blockers=blockers,
            metadata={'decision_status': decision.decision_status, 'auto_applicable': decision.auto_applicable},
        ))

    for decision in PortfolioExposureDecision.objects.select_related('linked_cluster_snapshot__linked_market').order_by('-created_at_decision')[:200]:
        reason_codes = _extract_reason_codes(decision.reason_codes)
        blockers = _make_blockers_from_status(decision.decision_status, reason_codes, decision.decision_type)
        if not _include_item(decision.decision_status, decision.decision_type, blockers):
            continue
        items.append(CollectedGovernanceItem(
            source_module=GovernanceReviewSourceModule.PORTFOLIO_GOVERNOR,
            source_type=GovernanceReviewSourceType.EXPOSURE_COORDINATION,
            source_object_id=decision.id,
            linked_market_id=decision.linked_cluster_snapshot.linked_market_id,
            title=f'Exposure coordination: {decision.decision_type}',
            summary=decision.decision_summary or 'Portfolio exposure coordination decision pending governance review.',
            reason_codes=reason_codes,
            blockers=blockers,
            metadata={'decision_status': decision.decision_status, 'auto_applicable': decision.auto_applicable},
        ))

    for decision in PortfolioExposureApplyDecision.objects.select_related('linked_exposure_decision__linked_cluster_snapshot__linked_market').order_by('-created_at_decision')[:200]:
        reason_codes = _extract_reason_codes(decision.reason_codes)
        blockers = _make_blockers_from_status(decision.apply_status, reason_codes, decision.apply_type)
        if not _include_item(decision.apply_status, decision.apply_type, blockers):
            continue
        linked_market_id = None
        if decision.linked_exposure_decision and decision.linked_exposure_decision.linked_cluster_snapshot:
            linked_market_id = decision.linked_exposure_decision.linked_cluster_snapshot.linked_market_id
        items.append(CollectedGovernanceItem(
            source_module=GovernanceReviewSourceModule.PORTFOLIO_GOVERNOR,
            source_type=GovernanceReviewSourceType.EXPOSURE_APPLY,
            source_object_id=decision.id,
            linked_market_id=linked_market_id,
            title=f'Exposure apply: {decision.apply_type}',
            summary=decision.apply_summary or 'Portfolio exposure apply decision pending governance review.',
            reason_codes=reason_codes,
            blockers=blockers,
            metadata={'apply_status': decision.apply_status, 'auto_applicable': decision.auto_applicable},
        ))

    return items
