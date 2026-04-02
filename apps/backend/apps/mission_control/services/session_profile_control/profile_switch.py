from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousProfileContextStatus,
    AutonomousProfileSwitchDecision,
    AutonomousProfileSwitchDecisionStatus,
    AutonomousProfileSwitchDecisionType,
    AutonomousProfileSwitchRecord,
    AutonomousProfileSwitchStatus,
    AutonomousRuntimeSession,
    AutonomousScheduleProfile,
    AutonomousSessionContextReview,
)
from apps.mission_control.services.session_timing import apply_schedule_profile, ensure_default_schedule_profiles

_SWITCH_COOLDOWN_MINUTES = 15


def _resolve_profile(slug: str) -> AutonomousScheduleProfile | None:
    return AutonomousScheduleProfile.objects.filter(slug=slug, is_active=True).first()


def decide_profile_switch(*, session: AutonomousRuntimeSession, context_review: AutonomousSessionContextReview, selection_run=None) -> AutonomousProfileSwitchDecision:
    ensure_default_schedule_profiles()
    from_profile = session.linked_schedule_profile
    from_slug = from_profile.slug if from_profile else ''

    decision_type = AutonomousProfileSwitchDecisionType.KEEP_CURRENT_PROFILE
    to_profile = from_profile
    reason_codes = list(context_review.reason_codes or [])

    if context_review.context_status == AutonomousProfileContextStatus.BLOCKED:
        decision_type = AutonomousProfileSwitchDecisionType.BLOCK_PROFILE_SWITCH
        reason_codes.append('context_blocked')
        to_profile = from_profile
    elif context_review.context_status == AutonomousProfileContextStatus.NEEDS_MORE_CONSERVATIVE_PROFILE:
        if context_review.activity_state == 'REPEATED_NO_ACTION' and context_review.signal_pressure_state == 'QUIET':
            to_profile = _resolve_profile('monitor_heavy') or _resolve_profile('conservative_quiet')
            decision_type = AutonomousProfileSwitchDecisionType.SWITCH_TO_MONITOR_HEAVY
            reason_codes.append('quiet_no_action_shift_monitor')
        else:
            to_profile = _resolve_profile('conservative_quiet')
            decision_type = AutonomousProfileSwitchDecisionType.SWITCH_TO_CONSERVATIVE_QUIET
            reason_codes.append('conservative_shift_required')
    elif context_review.context_status == AutonomousProfileContextStatus.NEEDS_MORE_ACTIVE_PROFILE:
        to_profile = _resolve_profile('balanced_local')
        decision_type = AutonomousProfileSwitchDecisionType.SWITCH_TO_BALANCED_LOCAL
        reason_codes.append('restore_balanced')
    elif context_review.context_status in {AutonomousProfileContextStatus.HOLD_CURRENT, AutonomousProfileContextStatus.STABLE}:
        decision_type = AutonomousProfileSwitchDecisionType.KEEP_CURRENT_PROFILE
        to_profile = from_profile
        reason_codes.append('hold_profile')
    else:
        decision_type = AutonomousProfileSwitchDecisionType.REQUIRE_MANUAL_PROFILE_REVIEW
        reason_codes.append('manual_review_fallback')

    if decision_type.startswith('SWITCH_') and to_profile and from_slug == to_profile.slug:
        decision_type = AutonomousProfileSwitchDecisionType.KEEP_CURRENT_PROFILE
        reason_codes.append('target_profile_already_active')

    latest_record = session.profile_switch_records.order_by('-created_at', '-id').first()
    in_hysteresis_window = bool(
        latest_record and latest_record.created_at >= timezone.now() - timedelta(minutes=_SWITCH_COOLDOWN_MINUTES)
    )
    if in_hysteresis_window and decision_type.startswith('SWITCH_'):
        decision_type = AutonomousProfileSwitchDecisionType.KEEP_CURRENT_PROFILE
        reason_codes.append('switch_hysteresis_window')

    decision = AutonomousProfileSwitchDecision.objects.create(
        linked_selection_run=selection_run,
        linked_session=session,
        linked_context_review=context_review,
        from_profile=from_profile,
        to_profile=to_profile,
        decision_type=decision_type,
        decision_status=AutonomousProfileSwitchDecisionStatus.PROPOSED,
        decision_summary=f'decision={decision_type} from={from_slug or "none"} to={(to_profile.slug if to_profile else "none")}',
        reason_codes=list(dict.fromkeys(reason_codes)),
        metadata={
            'hysteresis_minutes': _SWITCH_COOLDOWN_MINUTES,
            'hysteresis_active': in_hysteresis_window,
            'latest_switch_record_id': latest_record.id if latest_record else None,
        },
    )
    return decision


def apply_profile_switch_decision(*, decision: AutonomousProfileSwitchDecision, automatic: bool = True) -> AutonomousProfileSwitchRecord | None:
    session = decision.linked_session
    previous_profile = decision.from_profile or session.linked_schedule_profile

    if decision.decision_type == AutonomousProfileSwitchDecisionType.BLOCK_PROFILE_SWITCH:
        decision.decision_status = AutonomousProfileSwitchDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return None

    if decision.decision_type in {
        AutonomousProfileSwitchDecisionType.KEEP_CURRENT_PROFILE,
        AutonomousProfileSwitchDecisionType.REQUIRE_MANUAL_PROFILE_REVIEW,
    }:
        decision.decision_status = AutonomousProfileSwitchDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return None

    if not decision.to_profile:
        decision.decision_status = AutonomousProfileSwitchDecisionStatus.BLOCKED
        decision.reason_codes = list(dict.fromkeys([*(decision.reason_codes or []), 'missing_target_profile']))
        decision.save(update_fields=['decision_status', 'reason_codes', 'updated_at'])
        return None

    apply_schedule_profile(session=session, profile=decision.to_profile)
    decision.decision_status = AutonomousProfileSwitchDecisionStatus.APPLIED
    decision.save(update_fields=['decision_status', 'updated_at'])

    return AutonomousProfileSwitchRecord.objects.create(
        linked_selection_run=decision.linked_selection_run,
        linked_session=session,
        linked_switch_decision=decision,
        previous_profile=previous_profile,
        applied_profile=decision.to_profile,
        switch_status=AutonomousProfileSwitchStatus.APPLIED,
        switch_summary=f'Applied profile switch to {decision.to_profile.slug}.',
        metadata={'automatic': automatic},
    )
