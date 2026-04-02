from __future__ import annotations

from django.utils import timezone

from apps.autonomous_trader.models import AutonomousDispatchStatus
from apps.mission_control.models import AutonomousRuntimeSessionStatus
from apps.portfolio_governor.models import (
    PortfolioExposureApplyDecision,
    PortfolioExposureApplyDecisionStatus,
    PortfolioExposureApplyEffectType,
    PortfolioExposureApplyRecord,
    PortfolioExposureApplyRecordStatus,
    PortfolioExposureApplyTarget,
    PortfolioExposureApplyTargetStatus,
    PortfolioExposureApplyType,
    PortfolioExposureDecisionStatus,
)


class ApplyExecutionResult:
    def __init__(self, status: str, effect_type: str, summary: str, metadata: dict):
        self.status = status
        self.effect_type = effect_type
        self.summary = summary
        self.metadata = metadata


def _mark_target(target: PortfolioExposureApplyTarget, status: str, summary: str):
    target.target_status = status
    target.target_summary = summary
    target.save(update_fields=['target_status', 'target_summary', 'updated_at'])


def execute_apply_decision(*, apply_decision: PortfolioExposureApplyDecision, force_apply: bool = False) -> PortfolioExposureApplyRecord:
    decision = apply_decision.linked_exposure_decision
    targets = list(apply_decision.linked_apply_run.targets.filter(linked_exposure_decision=decision))

    if apply_decision.apply_status in [PortfolioExposureApplyDecisionStatus.BLOCKED, PortfolioExposureApplyDecisionStatus.FAILED]:
        return PortfolioExposureApplyRecord.objects.create(
            linked_apply_decision=apply_decision,
            record_status=PortfolioExposureApplyRecordStatus.BLOCKED,
            effect_type=PortfolioExposureApplyEffectType.MANUAL_REVIEW_ONLY,
            record_summary='Apply decision is blocked and cannot be executed automatically.',
            metadata={'blocked_apply_status': apply_decision.apply_status},
        )

    if not apply_decision.auto_applicable and not force_apply:
        apply_decision.apply_status = PortfolioExposureApplyDecisionStatus.SKIPPED
        apply_decision.apply_summary = 'Manual review required before apply execution.'
        apply_decision.save(update_fields=['apply_status', 'apply_summary', 'updated_at'])
        decision.decision_status = PortfolioExposureDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        for target in targets:
            _mark_target(target, PortfolioExposureApplyTargetStatus.SKIPPED, 'Skipped: waiting for manual exposure apply review.')
        return PortfolioExposureApplyRecord.objects.create(
            linked_apply_decision=apply_decision,
            record_status=PortfolioExposureApplyRecordStatus.SKIPPED,
            effect_type=PortfolioExposureApplyEffectType.MANUAL_REVIEW_ONLY,
            record_summary='Decision was not auto-applied and remains manual-review only.',
            metadata={'manual_review_required': True},
        )

    applied_count = 0
    deferred_dispatches = 0
    parked_sessions = 0
    paused_sessions = 0
    throttled_admission_paths = 0

    if apply_decision.apply_type == PortfolioExposureApplyType.APPLY_DEFER_PENDING_DISPATCH:
        for target in targets:
            if target.target_type != 'PENDING_DISPATCH' or target.linked_dispatch_record is None:
                continue
            dispatch = target.linked_dispatch_record
            if dispatch.dispatch_status == AutonomousDispatchStatus.QUEUED:
                dispatch.dispatch_status = AutonomousDispatchStatus.SKIPPED
                dispatch.dispatch_summary = 'Deferred by conservative portfolio exposure apply bridge.'
                dispatch.metadata = {
                    **dispatch.metadata,
                    'deferred_by_exposure_apply': True,
                    'exposure_decision_id': decision.id,
                    'deferred_at': timezone.now().isoformat(),
                }
                dispatch.save(update_fields=['dispatch_status', 'dispatch_summary', 'metadata', 'updated_at'])
                deferred_dispatches += 1
                applied_count += 1
                _mark_target(target, PortfolioExposureApplyTargetStatus.APPLIED, f'Dispatch #{dispatch.id} deferred conservatively.')
            else:
                _mark_target(target, PortfolioExposureApplyTargetStatus.SKIPPED, f'Dispatch #{dispatch.id} not queued; defer skipped.')

    if apply_decision.apply_type in [PortfolioExposureApplyType.APPLY_PARK_SESSION, PortfolioExposureApplyType.APPLY_PAUSE_CLUSTER_ACTIVITY]:
        for target in targets:
            if target.target_type != 'SESSION' or target.linked_session is None:
                continue
            session = target.linked_session
            if session.session_status == AutonomousRuntimeSessionStatus.RUNNING:
                session.session_status = AutonomousRuntimeSessionStatus.PAUSED
                pause_codes = list(session.pause_reason_codes or [])
                pause_codes.append('exposure_apply')
                session.pause_reason_codes = sorted(set(pause_codes))
                session.metadata = {
                    **session.metadata,
                    'exposure_apply_gate': True,
                    'exposure_decision_id': decision.id,
                    'apply_type': apply_decision.apply_type,
                }
                session.save(update_fields=['session_status', 'pause_reason_codes', 'metadata', 'updated_at'])
                applied_count += 1
                if apply_decision.apply_type == PortfolioExposureApplyType.APPLY_PARK_SESSION:
                    parked_sessions += 1
                    _mark_target(target, PortfolioExposureApplyTargetStatus.APPLIED, f'Session #{session.id} parked conservatively.')
                else:
                    paused_sessions += 1
                    _mark_target(target, PortfolioExposureApplyTargetStatus.APPLIED, f'Session #{session.id} paused by cluster gate.')
            else:
                _mark_target(target, PortfolioExposureApplyTargetStatus.SKIPPED, f'Session #{session.id} not running; unchanged.')

    if apply_decision.apply_type == PortfolioExposureApplyType.APPLY_THROTTLE_NEW_ENTRIES:
        cluster = decision.linked_cluster_snapshot
        cluster.metadata = {
            **cluster.metadata,
            'exposure_new_entries_throttled': True,
            'throttle_source_decision_id': decision.id,
        }
        cluster.save(update_fields=['metadata', 'updated_at'])
        for target in targets:
            if target.target_type in ['CLUSTER_GATE', 'ADMISSION_PATH']:
                throttled_admission_paths += 1
                applied_count += 1
                _mark_target(target, PortfolioExposureApplyTargetStatus.APPLIED, 'Cluster admission path throttled for new entries.')

    if apply_decision.apply_type == PortfolioExposureApplyType.APPLY_NO_CHANGE:
        for target in targets:
            _mark_target(target, PortfolioExposureApplyTargetStatus.SKIPPED, 'No exposure runtime change required.')

    if apply_decision.apply_type == PortfolioExposureApplyType.APPLY_MANUAL_REVIEW_ONLY:
        for target in targets:
            _mark_target(target, PortfolioExposureApplyTargetStatus.BLOCKED, 'Manual exposure apply review required before runtime changes.')

    if apply_decision.apply_type == PortfolioExposureApplyType.APPLY_PAUSE_CLUSTER_ACTIVITY:
        for target in targets:
            if target.target_type == 'CLUSTER_GATE':
                _mark_target(target, PortfolioExposureApplyTargetStatus.APPLIED, 'Cluster gate paused for new activity.')

    if applied_count > 0:
        apply_decision.apply_status = PortfolioExposureApplyDecisionStatus.APPLIED
        decision.decision_status = PortfolioExposureDecisionStatus.APPLIED
        record_status = PortfolioExposureApplyRecordStatus.APPLIED
    elif apply_decision.apply_type in [PortfolioExposureApplyType.APPLY_MANUAL_REVIEW_ONLY, PortfolioExposureApplyType.APPLY_NO_CHANGE]:
        apply_decision.apply_status = PortfolioExposureApplyDecisionStatus.SKIPPED
        decision.decision_status = PortfolioExposureDecisionStatus.SKIPPED
        record_status = PortfolioExposureApplyRecordStatus.SKIPPED
    else:
        apply_decision.apply_status = PortfolioExposureApplyDecisionStatus.BLOCKED
        decision.decision_status = PortfolioExposureDecisionStatus.BLOCKED
        record_status = PortfolioExposureApplyRecordStatus.BLOCKED

    apply_decision.apply_summary = f'Apply bridge updated runtime with {applied_count} conservative target changes.'
    apply_decision.metadata = {
        **apply_decision.metadata,
        'deferred_dispatches': deferred_dispatches,
        'parked_sessions': parked_sessions,
        'paused_sessions': paused_sessions,
        'throttled_admission_paths': throttled_admission_paths,
    }
    apply_decision.save(update_fields=['apply_status', 'apply_summary', 'metadata', 'updated_at'])
    decision.save(update_fields=['decision_status', 'updated_at'])

    if apply_decision.apply_type == PortfolioExposureApplyType.APPLY_DEFER_PENDING_DISPATCH:
        effect_type = PortfolioExposureApplyEffectType.DISPATCH_DEFERRED
    elif apply_decision.apply_type == PortfolioExposureApplyType.APPLY_PARK_SESSION:
        effect_type = PortfolioExposureApplyEffectType.SESSION_PARKED
    elif apply_decision.apply_type == PortfolioExposureApplyType.APPLY_PAUSE_CLUSTER_ACTIVITY:
        effect_type = PortfolioExposureApplyEffectType.CLUSTER_ACTIVITY_PAUSED
    elif apply_decision.apply_type == PortfolioExposureApplyType.APPLY_THROTTLE_NEW_ENTRIES:
        effect_type = PortfolioExposureApplyEffectType.NEW_ENTRIES_THROTTLED
    elif apply_decision.apply_type == PortfolioExposureApplyType.APPLY_MANUAL_REVIEW_ONLY:
        effect_type = PortfolioExposureApplyEffectType.MANUAL_REVIEW_ONLY
    else:
        effect_type = PortfolioExposureApplyEffectType.NO_CHANGE

    return PortfolioExposureApplyRecord.objects.create(
        linked_apply_decision=apply_decision,
        record_status=record_status,
        effect_type=effect_type,
        record_summary=apply_decision.apply_summary,
        metadata=apply_decision.metadata,
    )
