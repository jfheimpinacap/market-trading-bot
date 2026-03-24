from __future__ import annotations

from dataclasses import asdict, dataclass

from django.db.models import Q

from apps.continuous_demo.models import ContinuousDemoCycleRun, CycleStatus
from apps.paper_trading.services.portfolio import get_active_account
from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.models import TradeProposal
from apps.safety_guard.models import SafetyEvent, SafetyEventSource, SafetyEventType, SafetyPolicyConfig, SafetySeverity, SafetyStatus
from apps.safety_guard.services.cooldown import trigger_cooldown
from apps.safety_guard.services.kill_switch import enable_kill_switch, get_or_create_config
from apps.safety_guard.services.limits import evaluate_exposure_limits, evaluate_loss_limits


@dataclass
class SafetyDecision:
    allowed: bool
    classification: str
    reasons: list[str]
    requires_manual_approval: bool = False




def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, 'as_tuple'):
        return str(value)
    return value

def _record_event(*, event_type: str, severity: str, source: str, message: str, details: dict | None = None, related_session_id: int | None = None, related_cycle_id: int | None = None, related_market_id: int | None = None) -> None:
    SafetyEvent.objects.create(
        event_type=event_type,
        severity=severity,
        source=source,
        related_session_id=related_session_id,
        related_cycle_id=related_cycle_id,
        related_market_id=related_market_id,
        message=message,
        details=_json_safe(details or {}),
    )


def evaluate_auto_execution(*, proposal: TradeProposal, auto_trades_so_far: int, session_id: int | None = None, cycle_id: int | None = None, source: str = SafetyEventSource.SEMI_AUTO) -> SafetyDecision:
    config = get_or_create_config()

    if config.kill_switch_enabled:
        return SafetyDecision(allowed=False, classification='kill_switch', reasons=['Kill switch is enabled.'])

    if config.hard_stop_active:
        return SafetyDecision(allowed=False, classification='hard_stop', reasons=['Hard stop is active; manual intervention required.'])

    if config.cooldown_until_cycle is not None and cycle_id is not None and cycle_id <= config.cooldown_until_cycle:
        return SafetyDecision(
            allowed=False,
            classification='cooldown',
            reasons=['Cooldown is active. Auto execution is temporarily disabled.'],
            requires_manual_approval=True,
        )

    reasons: list[str] = []
    requires_manual_approval = False

    if auto_trades_so_far >= config.max_auto_trades_per_cycle:
        reasons.append(f'Max auto trades per cycle reached ({config.max_auto_trades_per_cycle}).')
        requires_manual_approval = True

    if proposal.suggested_quantity and proposal.suggested_quantity >= config.require_manual_approval_above_quantity:
        reasons.append('Suggested quantity is above manual-approval threshold.')
        requires_manual_approval = True

    if session_id is not None:
        from apps.continuous_demo.models import ContinuousDemoSession

        session = ContinuousDemoSession.objects.filter(pk=session_id).first()
        if session and (session.total_auto_executed + auto_trades_so_far) >= config.max_auto_trades_per_session:
            reasons.append(f'Max auto trades per session reached ({config.max_auto_trades_per_session}).')
            requires_manual_approval = True

    exposure_ok, exposure_reasons, snapshot = evaluate_exposure_limits(proposal=proposal, config=config)
    if not exposure_ok:
        reasons.extend(exposure_reasons)
        _record_event(
            event_type=SafetyEventType.EXPOSURE_LIMIT_HIT,
            severity=SafetySeverity.WARNING,
            source=source,
            message='Exposure guardrail prevented auto execution.',
            details=snapshot,
            related_session_id=session_id,
            related_cycle_id=cycle_id,
            related_market_id=proposal.market_id,
        )
        return SafetyDecision(allowed=False, classification='blocked', reasons=reasons)

    if snapshot['estimated_cost'] >= config.require_manual_approval_above_exposure:
        reasons.append('Estimated exposure is above approval-escalation threshold.')
        requires_manual_approval = True

    account = proposal.paper_account
    if account:
        losses_ok, loss_reasons, loss_details = evaluate_loss_limits(
            config=config,
            equity=account.equity,
            initial_balance=account.initial_balance,
            unrealized_pnl=account.unrealized_pnl,
        )
        if not losses_ok:
            reasons.extend(loss_reasons)
            _record_event(
                event_type=SafetyEventType.DRAWDOWN_LIMIT_HIT,
                severity=SafetySeverity.CRITICAL,
                source=SafetyEventSource.PORTFOLIO,
                message='Loss guardrail hit; switching to hard stop.',
                details=loss_details,
                related_session_id=session_id,
                related_cycle_id=cycle_id,
            )
            config.hard_stop_active = True
            config.status = SafetyStatus.HARD_STOP
            config.status_message = 'Hard stop enabled because drawdown/loss threshold was exceeded.'
            config.save(update_fields=['hard_stop_active', 'status', 'status_message', 'updated_at'])
            return SafetyDecision(allowed=False, classification='hard_stop', reasons=reasons)

    if requires_manual_approval and proposal.policy_decision == ApprovalDecisionType.AUTO_APPROVE:
        _record_event(
            event_type=SafetyEventType.APPROVAL_ESCALATION,
            severity=SafetySeverity.WARNING,
            source=source,
            message='Safety guard escalated AUTO_APPROVE proposal to APPROVAL_REQUIRED.',
            details={'reasons': reasons},
            related_session_id=session_id,
            related_cycle_id=cycle_id,
            related_market_id=proposal.market_id,
        )
        return SafetyDecision(allowed=False, classification='approval_required', reasons=reasons, requires_manual_approval=True)

    return SafetyDecision(allowed=True, classification='allow_auto', reasons=reasons)


def evaluate_cycle_health(*, cycle: ContinuousDemoCycleRun, source: str = SafetyEventSource.CONTINUOUS_DEMO) -> SafetyPolicyConfig:
    config = get_or_create_config()

    if cycle.status in {CycleStatus.FAILED, CycleStatus.PARTIAL}:
        config.consecutive_error_count += 1
        config.consecutive_failed_cycles_count += 1 if cycle.status == CycleStatus.FAILED else 0
    else:
        config.consecutive_error_count = 0
        config.consecutive_failed_cycles_count = 0

    if cycle.blocked_count > 0:
        config.consecutive_blocked_runs += 1
    else:
        config.consecutive_blocked_runs = 0

    latest_reviews = list(
        TradeReview.objects.filter(~Q(outcome=TradeReviewOutcome.NEUTRAL)).order_by('-reviewed_at', '-id')[: config.max_consecutive_unfavorable_reviews]
    )
    if latest_reviews and all(item.outcome == TradeReviewOutcome.UNFAVORABLE for item in latest_reviews):
        config.consecutive_unfavorable_reviews_count = len(latest_reviews)
    else:
        config.consecutive_unfavorable_reviews_count = 0

    if config.consecutive_error_count >= config.hard_stop_after_error_count:
        config.hard_stop_active = True
        config.status = SafetyStatus.HARD_STOP
        config.status_message = 'Hard stop activated after repeated cycle errors.'
        config.save(update_fields=[
            'consecutive_error_count',
            'consecutive_failed_cycles_count',
            'consecutive_blocked_runs',
            'consecutive_unfavorable_reviews_count',
            'hard_stop_active',
            'status',
            'status_message',
            'updated_at',
        ])
        _record_event(
            event_type=SafetyEventType.ERROR_LIMIT_HIT,
            severity=SafetySeverity.CRITICAL,
            source=source,
            message='Hard stop activated due to error threshold.',
            related_session_id=cycle.session_id,
            related_cycle_id=cycle.id,
            details={'consecutive_error_count': config.consecutive_error_count},
        )
        enable_kill_switch(source=source, message='Kill switch auto-enabled after repeated cycle errors.')
        return config

    if (
        config.consecutive_blocked_runs >= config.cooldown_after_block_count
        or config.consecutive_unfavorable_reviews_count >= config.max_consecutive_unfavorable_reviews
        or config.consecutive_failed_cycles_count >= config.max_consecutive_failed_cycles
    ):
        trigger_cooldown(
            current_cycle=cycle.cycle_number,
            source=source,
            reason='Safety cooldown triggered after repeated unfavorable operational signals.',
            details={
                'consecutive_blocked_runs': config.consecutive_blocked_runs,
                'consecutive_unfavorable_reviews_count': config.consecutive_unfavorable_reviews_count,
                'consecutive_failed_cycles_count': config.consecutive_failed_cycles_count,
            },
        )
        return get_or_create_config()

    if not config.hard_stop_active and not config.kill_switch_enabled:
        config.status = SafetyStatus.HEALTHY
        config.status_message = 'Safety checks passed in latest cycle.'

    config.save(update_fields=[
        'consecutive_error_count',
        'consecutive_failed_cycles_count',
        'consecutive_blocked_runs',
        'consecutive_unfavorable_reviews_count',
        'status',
        'status_message',
        'updated_at',
    ])
    return config


def get_safety_status() -> dict:
    config = get_or_create_config()
    account = get_active_account()
    latest_event = SafetyEvent.objects.order_by('-created_at', '-id').first()

    return {
        'status': config.status,
        'status_message': config.status_message,
        'kill_switch_enabled': config.kill_switch_enabled,
        'hard_stop_active': config.hard_stop_active,
        'cooldown_until_cycle': config.cooldown_until_cycle,
        'paused_by_safety': config.paused_by_safety,
        'account_snapshot': {
            'equity': str(account.equity),
            'initial_balance': str(account.initial_balance),
            'unrealized_pnl': str(account.unrealized_pnl),
            'realized_pnl': str(account.realized_pnl),
            'total_pnl': str(account.total_pnl),
        } if account else None,
        'limits': {
            'max_auto_trades_per_cycle': config.max_auto_trades_per_cycle,
            'max_auto_trades_per_session': config.max_auto_trades_per_session,
            'max_position_value_per_market': str(config.max_position_value_per_market),
            'max_total_open_exposure': str(config.max_total_open_exposure),
            'max_daily_or_session_drawdown': str(config.max_daily_or_session_drawdown),
            'max_unrealized_loss_threshold': str(config.max_unrealized_loss_threshold),
            'cooldown_after_block_count': config.cooldown_after_block_count,
            'cooldown_cycles': config.cooldown_cycles,
            'hard_stop_after_error_count': config.hard_stop_after_error_count,
            'require_manual_approval_above_quantity': str(config.require_manual_approval_above_quantity),
            'require_manual_approval_above_exposure': str(config.require_manual_approval_above_exposure),
        },
        'counters': {
            'consecutive_blocked_runs': config.consecutive_blocked_runs,
            'consecutive_failed_cycles_count': config.consecutive_failed_cycles_count,
            'consecutive_unfavorable_reviews_count': config.consecutive_unfavorable_reviews_count,
            'consecutive_error_count': config.consecutive_error_count,
        },
        'last_event': {
            'id': latest_event.id,
            'event_type': latest_event.event_type,
            'severity': latest_event.severity,
            'source': latest_event.source,
            'message': latest_event.message,
            'created_at': latest_event.created_at,
        } if latest_event else None,
    }
