from __future__ import annotations

from typing import Any

from apps.mission_control.services.live_paper_attention_bridge import (
    ATTENTION_MODE_BLOCKED,
    ATTENTION_MODE_DEGRADED,
    ATTENTION_MODE_REVIEW_NOW,
    get_live_paper_attention_alert_status,
)
from apps.mission_control.services.live_paper_autonomy_funnel import (
    FUNNEL_STALLED,
    FUNNEL_THIN_FLOW,
    build_live_paper_autonomy_funnel_snapshot,
)
from apps.mission_control.services.live_paper_bootstrap import PRESET_NAME, get_live_paper_bootstrap_status
from apps.mission_control.services.live_paper_trial_history import list_live_paper_trial_history
from apps.mission_control.services.live_paper_trial_trend import (
    READINESS_NOT_READY,
    READINESS_READY,
    TREND_IMPROVING,
    TREND_STABLE,
    build_live_paper_trial_trend_digest,
)
from apps.mission_control.services.live_paper_validation import (
    VALIDATION_BLOCKED,
    VALIDATION_READY,
    VALIDATION_WARNING,
    build_live_paper_validation_digest,
)
from apps.mission_control.services.state_consistency import (
    STATE_GATE_BLOCKED_ON_STALE_VIEW,
    build_state_consistency_snapshot,
)
from apps.paper_trading.services.portfolio import (
    build_account_financial_summary,
    build_account_summary,
    get_active_account,
)

GATE_ALLOW = 'ALLOW'
GATE_ALLOW_WITH_CAUTION = 'ALLOW_WITH_CAUTION'
GATE_BLOCK = 'BLOCK'

_CHECK_PASS = 'PASS'
_CHECK_WARN = 'WARN'
_CHECK_FAIL = 'FAIL'

_REASON_VALIDATION_READY = 'VALIDATION_READY'
_REASON_VALIDATION_WARNING = 'VALIDATION_WARNING'
_REASON_VALIDATION_BLOCKED = 'VALIDATION_BLOCKED'
_REASON_TRIAL_TREND_READY = 'TRIAL_TREND_READY'
_REASON_RECENT_WARNINGS = 'RECENT_WARNINGS'
_REASON_INSUFFICIENT_TRIAL_DATA = 'INSUFFICIENT_TRIAL_DATA'
_REASON_LATEST_TRIAL_FAIL = 'LATEST_TRIAL_FAIL'
_REASON_READINESS_NOT_READY = 'READINESS_NOT_READY'
_REASON_ATTENTION_DEGRADED = 'ATTENTION_DEGRADED'
_REASON_ATTENTION_BLOCKING = 'ATTENTION_BLOCKING'
_REASON_FUNNEL_THIN_FLOW = 'FUNNEL_THIN_FLOW'
_REASON_FUNNEL_STALLED = 'FUNNEL_STALLED'
_REASON_STALE_VIEW_BLOCK_CONFIRMED = 'STALE_VIEW_BLOCK_CONFIRMED_NO_RECENT_ALIGNED_EVIDENCE'
_REASON_STALE_VIEW_BLOCK_DEGRADED = 'STALE_VIEW_BLOCK_DEGRADED_RECENT_ALIGNED_EVIDENCE'
_REASON_STALE_VIEW_REVIEW_REQUIRED = 'STALE_VIEW_REVIEW_REQUIRED'


def _check(*, check_name: str, status: str, summary: str) -> dict[str, str]:
    return {
        'check_name': check_name,
        'status': status,
        'summary': summary,
    }


def _normalize_latest_trial_status(*, trend: dict[str, Any], history: dict[str, Any]) -> str | None:
    trend_status = str(trend.get('latest_trial_status') or '').upper().strip()
    if trend_status in {'PASS', 'WARN', 'FAIL'}:
        return trend_status
    history_status = str(history.get('latest_trial_status') or '').upper().strip()
    if history_status in {'PASS', 'WARN', 'FAIL'}:
        return history_status
    return None


def build_extended_paper_run_gate(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME

    validation = build_live_paper_validation_digest(preset_name=target_preset)
    trend = build_live_paper_trial_trend_digest(limit=5, preset=target_preset)
    history = list_live_paper_trial_history(limit=5)
    attention = get_live_paper_attention_alert_status()
    funnel = build_live_paper_autonomy_funnel_snapshot(window_minutes=60, preset_name=target_preset)
    bootstrap = get_live_paper_bootstrap_status(preset_name=target_preset)
    account = get_active_account()
    portfolio_summary = build_account_summary(account=account)
    portfolio_financial = build_account_financial_summary(account=account)
    state_consistency = build_state_consistency_snapshot(
        funnel=funnel,
        portfolio_summary={
            'open_positions': int(portfolio_summary.get('open_positions_count') or 0),
            'recent_trades_count': len(portfolio_summary.get('recent_trades') or []),
            'account_summary_status': str(portfolio_financial.get('summary_status') or ''),
        },
        funnel_session_detected=None,
        portfolio_session_detected=None,
        funnel_scope=None,
        portfolio_scope=account.slug,
        runtime_status={
            'session_active': bool(bootstrap.get('session_active')),
            'heartbeat_active': bool(bootstrap.get('heartbeat_active')),
            'current_session_status': str(bootstrap.get('current_session_status') or ''),
        },
    )

    validation_status = str(validation.get('validation_status') or VALIDATION_BLOCKED).upper()
    readiness_status = str(trend.get('readiness_status') or READINESS_NOT_READY).upper()
    trend_status = str(trend.get('trend_status') or 'INSUFFICIENT_DATA').upper()
    latest_trial_status = _normalize_latest_trial_status(trend=trend, history=history)
    attention_mode = str(attention.get('attention_mode') or ATTENTION_MODE_REVIEW_NOW).upper()
    funnel_status = str(funnel.get('funnel_status') or FUNNEL_STALLED).upper()

    sample_size = int(trend.get('sample_size') or 0)
    counts = trend.get('counts') or {}
    warn_count = int(counts.get('warn_count') or 0)
    fail_count = int(counts.get('fail_count') or 0)

    block_by_attention = attention_mode in {ATTENTION_MODE_BLOCKED, ATTENTION_MODE_REVIEW_NOW}
    block_by_funnel = funnel_status == FUNNEL_STALLED and not state_consistency.should_ignore_funnel_block
    block_by_validation = validation_status == VALIDATION_BLOCKED
    block_by_readiness = readiness_status == READINESS_NOT_READY
    block_by_latest_trial = latest_trial_status == 'FAIL'
    block_by_missing_trials = latest_trial_status is None or sample_size < 1

    allow = (
        validation_status == VALIDATION_READY
        and readiness_status == READINESS_READY
        and latest_trial_status == 'PASS'
        and not block_by_attention
        and not block_by_funnel
    )

    block = any(
        [
            block_by_validation,
            block_by_readiness,
            block_by_latest_trial,
            block_by_attention,
            block_by_funnel,
            block_by_missing_trials,
        ]
    )

    gate_status = GATE_ALLOW_WITH_CAUTION
    if block:
        gate_status = GATE_BLOCK
    elif allow:
        gate_status = GATE_ALLOW

    reason_codes: list[str] = []
    if validation_status == VALIDATION_READY:
        reason_codes.append(_REASON_VALIDATION_READY)
    elif validation_status == VALIDATION_WARNING:
        reason_codes.append(_REASON_VALIDATION_WARNING)
    else:
        reason_codes.append(_REASON_VALIDATION_BLOCKED)

    if readiness_status == READINESS_READY and trend_status in {TREND_IMPROVING, TREND_STABLE}:
        reason_codes.append(_REASON_TRIAL_TREND_READY)

    if block_by_readiness:
        reason_codes.append(_REASON_READINESS_NOT_READY)
    if block_by_latest_trial:
        reason_codes.append(_REASON_LATEST_TRIAL_FAIL)
    if block_by_missing_trials:
        reason_codes.append(_REASON_INSUFFICIENT_TRIAL_DATA)
    if warn_count > 0 or (latest_trial_status == 'WARN') or trend_status == 'INSUFFICIENT_DATA':
        reason_codes.append(_REASON_RECENT_WARNINGS)

    if attention_mode == ATTENTION_MODE_DEGRADED:
        reason_codes.append(_REASON_ATTENTION_DEGRADED)
    if block_by_attention:
        reason_codes.append(_REASON_ATTENTION_BLOCKING)

    if funnel_status == FUNNEL_THIN_FLOW:
        reason_codes.append(_REASON_FUNNEL_THIN_FLOW)
    if block_by_funnel:
        reason_codes.append(_REASON_FUNNEL_STALLED)
        reason_codes.append(_REASON_STALE_VIEW_BLOCK_CONFIRMED)
    elif funnel_status == FUNNEL_STALLED and state_consistency.should_ignore_funnel_block:
        reason_codes.append(STATE_GATE_BLOCKED_ON_STALE_VIEW)
        reason_codes.append(_REASON_STALE_VIEW_BLOCK_DEGRADED)
        reason_codes.append(_REASON_STALE_VIEW_REVIEW_REQUIRED)

    validation_check_status = _CHECK_FAIL if validation_status == VALIDATION_BLOCKED else (_CHECK_WARN if validation_status == VALIDATION_WARNING else _CHECK_PASS)
    trend_check_status = _CHECK_FAIL if (readiness_status == READINESS_NOT_READY or trend_status == 'DEGRADING') else (_CHECK_WARN if trend_status == 'INSUFFICIENT_DATA' or latest_trial_status == 'WARN' else _CHECK_PASS)
    attention_check_status = _CHECK_FAIL if block_by_attention else (_CHECK_WARN if attention_mode == ATTENTION_MODE_DEGRADED else _CHECK_PASS)
    funnel_check_status = _CHECK_FAIL if block_by_funnel else (_CHECK_WARN if funnel_status == FUNNEL_THIN_FLOW else _CHECK_PASS)
    recent_quality_check_status = _CHECK_FAIL if (latest_trial_status == 'FAIL' or fail_count > 0 or sample_size < 1) else (_CHECK_WARN if latest_trial_status == 'WARN' or warn_count > 0 or sample_size < 2 else _CHECK_PASS)

    checks = [
        _check(
            check_name='validation',
            status=validation_check_status,
            summary=f'Validation status is {validation_status}.',
        ),
        _check(
            check_name='trial_trend',
            status=trend_check_status,
            summary=f'Trial trend={trend_status}, readiness={readiness_status}.',
        ),
        _check(
            check_name='operational_attention',
            status=attention_check_status,
            summary=f'Operational attention mode={attention_mode}.',
        ),
        _check(
            check_name='autonomy_funnel',
            status=funnel_check_status,
            summary=f'Autonomy funnel status={funnel_status}.',
        ),
        _check(
            check_name='recent_trial_quality',
            status=recent_quality_check_status,
            summary=f'Recent trial sample_size={sample_size}, warn_count={warn_count}, fail_count={fail_count}.',
        ),
    ]

    if gate_status == GATE_ALLOW:
        next_action_hint = 'Proceed to extended paper run'
    elif gate_status == GATE_BLOCK:
        if block_by_missing_trials:
            next_action_hint = 'Run another short trial before extending'
        else:
            next_action_hint = 'Do not start extended paper run yet'
    else:
        next_action_hint = 'Proceed cautiously and monitor the first cycles'

    gate_summary = (
        f'{gate_status}: validation={validation_status}, readiness={readiness_status}, latest_trial={latest_trial_status or "NONE"}, '
        f'attention={attention_mode}, funnel={funnel_status}, session_active={bool(bootstrap.get("session_active"))}, '
        f'heartbeat_active={bool(bootstrap.get("heartbeat_active"))}, consistency={state_consistency.summary.get("consistency_status")}.'
    )

    return {
        'preset_name': str(validation.get('preset_name') or target_preset),
        'gate_status': gate_status,
        'latest_trial_status': latest_trial_status,
        'trend_status': trend_status,
        'readiness_status': readiness_status,
        'validation_status': validation_status,
        'attention_mode': attention_mode,
        'funnel_status': funnel_status,
        'next_action_hint': next_action_hint,
        'gate_summary': gate_summary,
        'reason_codes': list(dict.fromkeys(reason_codes)),
        'checks': checks,
        'state_mismatch_summary': state_consistency.summary,
        'state_mismatch_examples': state_consistency.examples,
        'gate_source_summary': {
            'validation_source': 'build_live_paper_validation_digest',
            'readiness_source': 'build_live_paper_trial_trend_digest',
            'funnel_source': 'build_live_paper_autonomy_funnel_snapshot:rolling_60m',
            'portfolio_source': 'paper_trading.services.portfolio',
            'funnel_scope': target_preset,
            'portfolio_scope': account.slug,
        },
    }
