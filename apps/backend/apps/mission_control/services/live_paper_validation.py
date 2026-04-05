from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from apps.mission_control.services.live_paper_attention_bridge import (
    ATTENTION_MODE_BLOCKED,
    ATTENTION_MODE_REVIEW_NOW,
    get_live_paper_attention_alert_status,
)
from apps.mission_control.services.live_paper_bootstrap import PRESET_NAME, get_live_paper_bootstrap_status
from apps.mission_control.services.session_heartbeat import build_heartbeat_summary
from apps.paper_trading.models import PaperPortfolioSnapshot
from apps.paper_trading.services.portfolio import build_account_summary, get_active_account

VALIDATION_READY = 'READY'
VALIDATION_WARNING = 'WARNING'
VALIDATION_BLOCKED = 'BLOCKED'

CHECK_PASS = 'PASS'
CHECK_WARN = 'WARN'
CHECK_FAIL = 'FAIL'

BLOCKING_ATTENTION_MODES = {ATTENTION_MODE_BLOCKED, ATTENTION_MODE_REVIEW_NOW}


def _to_float(value: Any) -> float | None:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _check(*, name: str, status: str, summary: str) -> dict[str, str]:
    return {
        'check_name': name,
        'status': status,
        'summary': summary,
    }


@dataclass(frozen=True)
class ValidationSignals:
    preset_name: str
    session_active: bool
    heartbeat_active: bool
    attention_mode: str
    paper_account_ready: bool
    market_data_ready: bool
    portfolio_snapshot_ready: bool
    recent_activity_present: bool
    recent_trades_present: bool
    cash_available: float | None
    equity_available: float | None


def _collect_signals(*, preset_name: str) -> ValidationSignals:
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=preset_name)
    heartbeat_summary = build_heartbeat_summary()
    attention_status = get_live_paper_attention_alert_status()

    account = get_active_account()
    account_summary = build_account_summary(account=account)
    latest_snapshot = PaperPortfolioSnapshot.objects.filter(account=account).order_by('-captured_at', '-id').first()
    latest_run = heartbeat_summary.get('latest_run')
    recent_trades = account_summary.get('recent_trades') or []

    cash_available = _to_float(account.cash_balance)
    equity_available = _to_float(account.equity)

    snapshot_has_balances = bool(
        latest_snapshot
        and latest_snapshot.cash_balance is not None
        and latest_snapshot.equity is not None
    )

    recent_activity_present = bool(latest_run or recent_trades or latest_snapshot)

    return ValidationSignals(
        preset_name=str(bootstrap_status.get('preset_name') or preset_name),
        session_active=bool(bootstrap_status.get('session_active')),
        heartbeat_active=bool(bootstrap_status.get('heartbeat_active')),
        attention_mode=str(attention_status.get('attention_mode') or 'HEALTHY'),
        paper_account_ready=bool(account and account.is_active),
        market_data_ready=str(bootstrap_status.get('market_data_mode') or '').upper() == 'REAL_READ_ONLY',
        portfolio_snapshot_ready=snapshot_has_balances,
        recent_activity_present=recent_activity_present,
        recent_trades_present=bool(recent_trades),
        cash_available=cash_available,
        equity_available=equity_available,
    )


def _evaluate_validation(signals: ValidationSignals) -> tuple[str, str]:
    has_minimum_economic_state = signals.portfolio_snapshot_ready or (
        signals.cash_available is not None and signals.equity_available is not None
    )
    useful_evidence = signals.recent_activity_present or signals.recent_trades_present or has_minimum_economic_state

    blocked = (
        (not signals.session_active)
        or (not signals.heartbeat_active)
        or (signals.attention_mode in BLOCKING_ATTENTION_MODES)
        or (not signals.paper_account_ready)
        or (not has_minimum_economic_state)
    )
    if blocked:
        return VALIDATION_BLOCKED, _next_action_hint(status=VALIDATION_BLOCKED, signals=signals)

    warning = (
        signals.attention_mode == 'DEGRADED'
        or (not signals.portfolio_snapshot_ready)
        or (not useful_evidence)
        or (not signals.recent_activity_present)
        or (not signals.recent_trades_present)
    )
    if warning:
        return VALIDATION_WARNING, _next_action_hint(status=VALIDATION_WARNING, signals=signals)

    return VALIDATION_READY, _next_action_hint(status=VALIDATION_READY, signals=signals)


def _next_action_hint(*, status: str, signals: ValidationSignals) -> str:
    if not signals.session_active:
        return 'Start live paper autopilot'
    if not signals.heartbeat_active:
        return 'Refresh after first heartbeat'
    if not signals.paper_account_ready:
        return 'Paper account missing'
    if signals.attention_mode in BLOCKING_ATTENTION_MODES:
        return 'Review operational attention before running'
    if status == VALIDATION_WARNING and not signals.recent_activity_present:
        return 'Refresh after first heartbeat'
    if status == VALIDATION_WARNING and not signals.recent_trades_present:
        return 'Waiting for first paper trade'
    return 'V1 paper appears operational'


def build_live_paper_validation_digest(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    signals = _collect_signals(preset_name=target_preset)
    validation_status, next_action_hint = _evaluate_validation(signals)

    checks = [
        _check(
            name='bootstrap_session',
            status=CHECK_PASS if signals.session_active else CHECK_FAIL,
            summary='Autopilot session is active.' if signals.session_active else 'Autopilot session is not active.',
        ),
        _check(
            name='heartbeat_loop',
            status=CHECK_PASS if signals.heartbeat_active else CHECK_FAIL,
            summary='Heartbeat runner is active.' if signals.heartbeat_active else 'Heartbeat runner is not active.',
        ),
        _check(
            name='attention_bridge',
            status=CHECK_FAIL if signals.attention_mode in BLOCKING_ATTENTION_MODES else (CHECK_WARN if signals.attention_mode == 'DEGRADED' else CHECK_PASS),
            summary=f'Attention mode={signals.attention_mode}.',
        ),
        _check(
            name='paper_account',
            status=CHECK_PASS if signals.paper_account_ready else CHECK_FAIL,
            summary='Paper account available.' if signals.paper_account_ready else 'Paper account unavailable.',
        ),
        _check(
            name='portfolio_snapshot',
            status=CHECK_PASS if signals.portfolio_snapshot_ready else CHECK_WARN,
            summary='Portfolio snapshot with balances is available.' if signals.portfolio_snapshot_ready else 'Portfolio snapshot is missing or partial.',
        ),
        _check(
            name='recent_activity',
            status=CHECK_PASS if signals.recent_activity_present else CHECK_WARN,
            summary='Recent activity evidence present.' if signals.recent_activity_present else 'No recent activity evidence yet.',
        ),
        _check(
            name='recent_trades',
            status=CHECK_PASS if signals.recent_trades_present else CHECK_WARN,
            summary='Recent paper trades found.' if signals.recent_trades_present else 'No recent paper trades yet.',
        ),
    ]

    summary = (
        f'{validation_status}: session_active={signals.session_active} heartbeat_active={signals.heartbeat_active} '
        f'attention_mode={signals.attention_mode} paper_account_ready={signals.paper_account_ready} '
        f'portfolio_snapshot_ready={signals.portfolio_snapshot_ready} recent_activity_present={signals.recent_activity_present} '
        f'recent_trades_present={signals.recent_trades_present}.'
    )

    return {
        'preset_name': signals.preset_name,
        'validation_status': validation_status,
        'session_active': signals.session_active,
        'heartbeat_active': signals.heartbeat_active,
        'attention_mode': signals.attention_mode,
        'paper_account_ready': signals.paper_account_ready,
        'market_data_ready': signals.market_data_ready,
        'portfolio_snapshot_ready': signals.portfolio_snapshot_ready,
        'recent_activity_present': signals.recent_activity_present,
        'recent_trades_present': signals.recent_trades_present,
        'cash_available': signals.cash_available,
        'equity_available': signals.equity_available,
        'next_action_hint': next_action_hint,
        'validation_summary': summary,
        'checks': checks,
    }
