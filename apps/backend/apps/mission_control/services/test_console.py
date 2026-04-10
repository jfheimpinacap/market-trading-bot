from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from typing import Any

from django.utils import timezone

from apps.mission_control.models import AutonomousRuntimeSession, AutonomousRuntimeSessionStatus
from apps.mission_control.services.extended_paper_run_gate import GATE_ALLOW, GATE_ALLOW_WITH_CAUTION, build_extended_paper_run_gate
from apps.mission_control.services.extended_paper_run_launcher import get_extended_paper_run_status, launch_extended_paper_run
from apps.mission_control.services.live_paper_attention_bridge import get_live_paper_attention_alert_status
from apps.mission_control.services.live_paper_autonomy_funnel import build_live_paper_autonomy_funnel_snapshot
from apps.mission_control.services.live_paper_bootstrap import (
    MARKET_DATA_MODE_REAL_READ_ONLY,
    PAPER_EXECUTION_MODE_PAPER_ONLY,
    PRESET_NAME,
    bootstrap_live_read_only_paper_session,
    get_live_paper_bootstrap_status,
)
from apps.mission_control.services.live_paper_trial_run import run_live_paper_trial_run
from apps.mission_control.services.live_paper_trial_trend import build_live_paper_trial_trend_digest
from apps.mission_control.services.live_paper_validation import build_live_paper_validation_digest
from apps.mission_control.services.session_heartbeat import get_runner_state, pause_runner
from apps.mission_control.services.session_runtime import pause_session
from apps.paper_trading.services.portfolio import build_account_summary, get_active_account
from apps.research_agent.models import NarrativeSignal, NarrativeSignalStatus, SourceScanRun
from apps.research_agent.services.intelligence_handoff.run import run_consensus_review
from apps.research_agent.services.run import run_scan_agent

TEST_STATUS_IDLE = 'IDLE'
TEST_STATUS_RUNNING = 'RUNNING'
TEST_STATUS_STOPPED = 'STOPPED'
TEST_STATUS_COMPLETED = 'COMPLETED'
TEST_STATUS_COMPLETED_WITH_WARNINGS = 'COMPLETED_WITH_WARNINGS'
TEST_STATUS_BLOCKED = 'BLOCKED'
TEST_STATUS_FAILED = 'FAILED'

_PHASES = [
    'bootstrap',
    'scan',
    'consensus_review',
    'trial',
    'validation',
    'trend',
    'gate',
    'extended_run',
    'finalize',
]

_HISTORY_SIZE = 10


@dataclass
class _ConsoleState:
    status: dict[str, Any]
    last_log: dict[str, Any] | None
    history: deque[dict[str, Any]]


_state_lock = Lock()
_state = _ConsoleState(
    status={
        'test_status': TEST_STATUS_IDLE,
        'current_phase': None,
        'started_at': None,
        'ended_at': None,
        'preset_name': PRESET_NAME,
        'session_active': False,
        'heartbeat_active': False,
        'current_session_status': 'UNKNOWN',
        'validation_status': 'UNKNOWN',
        'trial_status': 'UNKNOWN',
        'trend_status': 'UNKNOWN',
        'readiness_status': 'UNKNOWN',
        'gate_status': 'UNKNOWN',
        'extended_run_status': 'UNKNOWN',
        'funnel_status': 'UNKNOWN',
        'handoff_summary': {},
        'attention_mode': 'UNKNOWN',
        'portfolio_summary': {},
        'scan_summary': {},
        'blocker_summary': [],
        'next_action_hint': 'Start test console run',
        'warnings': [],
        'errors': [],
        'reason_codes': [],
    },
    last_log=None,
    history=deque(maxlen=_HISTORY_SIZE),
)


def _to_float(value: Any) -> float | None:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _set_state(*, status: dict[str, Any] | None = None, log: dict[str, Any] | None = None, append_history: bool = False) -> None:
    with _state_lock:
        if status is not None:
            _state.status = deepcopy(status)
        if log is not None:
            _state.last_log = deepcopy(log)
            if append_history:
                _state.history.appendleft(deepcopy(log))


def _get_state_snapshot() -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    with _state_lock:
        return deepcopy(_state.status), deepcopy(_state.last_log), deepcopy(list(_state.history))


def _find_active_preset_session(*, preset_name: str) -> AutonomousRuntimeSession | None:
    return (
        AutonomousRuntimeSession.objects.filter(
            session_status__in=[AutonomousRuntimeSessionStatus.RUNNING, AutonomousRuntimeSessionStatus.PAUSED]
        )
        .order_by('-updated_at', '-id')
        .filter(metadata__autopilot_preset_name=preset_name)
        .first()
    )


def _build_portfolio_summary() -> dict[str, Any]:
    account = get_active_account()
    summary = build_account_summary(account=account)
    recent_trades = summary.get('recent_trades') or []
    return {
        'cash': _to_float(account.cash_balance),
        'equity': _to_float(account.equity),
        'realized_pnl': _to_float(account.realized_pnl),
        'unrealized_pnl': _to_float(account.unrealized_pnl),
        'open_positions': int(summary.get('open_positions_count') or 0),
        'recent_trades_count': len(recent_trades),
    }


def _build_scan_summary(scan_run: SourceScanRun | None = None) -> dict[str, Any]:
    latest = scan_run or SourceScanRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'runs': 0,
            'rss_items': 0,
            'reddit_items': 0,
            'x_items': 0,
            'deduped_items': 0,
            'clusters': 0,
            'shortlisted_signals': 0,
            'signals_total': 0,
        }

    source_counts = latest.source_counts or {}
    diagnostics = (latest.metadata or {}).get('scan_diagnostics') or {}
    shortlisted_signals = latest.signals.filter(status=NarrativeSignalStatus.SHORTLISTED).count()

    return {
        'runs': SourceScanRun.objects.count(),
        'latest_run_id': latest.id,
        'summary_window': 'latest_scan_run',
        'rss_items': int(source_counts.get('rss_count') or 0),
        'reddit_items': int(source_counts.get('reddit_count') or 0),
        'x_items': int(source_counts.get('x_count') or 0),
        'raw_items': int(latest.raw_item_count or 0),
        'deduped_items': int(latest.deduped_item_count or 0),
        'clusters': int(latest.clustered_count or 0),
        'shortlisted_signals': int(shortlisted_signals),
        'signals_total': int(latest.signal_count or 0),
        'source_mode': str(diagnostics.get('source_mode') or ''),
        'rss_enabled': bool(diagnostics.get('rss_enabled')),
        'reddit_enabled': bool(diagnostics.get('reddit_enabled')),
        'x_enabled': bool(diagnostics.get('x_enabled')),
        'rss_fetch_attempted': bool(diagnostics.get('rss_fetch_attempted')),
        'reddit_fetch_attempted': bool(diagnostics.get('reddit_fetch_attempted')),
        'x_fetch_attempted': bool(diagnostics.get('x_fetch_attempted')),
        'zero_signal_reason_codes': list(diagnostics.get('zero_signal_reason_codes') or []),
        'diagnostic_summary': str(diagnostics.get('diagnostic_summary') or ''),
        'demo_fallback_used': bool((latest.metadata or {}).get('demo_fallback_used')),
        'summary': str(getattr(latest, 'summary', '') or ''),
    }


def _sync_operational_snapshot(*, payload: dict[str, Any], preset_name: str, scan_run: SourceScanRun | None = None) -> None:
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=preset_name)
    validation = build_live_paper_validation_digest(preset_name=preset_name)
    trend = build_live_paper_trial_trend_digest(limit=5, preset=preset_name)
    gate = build_extended_paper_run_gate(preset_name=preset_name)
    extended = get_extended_paper_run_status(preset_name=preset_name)
    attention = get_live_paper_attention_alert_status()
    funnel = build_live_paper_autonomy_funnel_snapshot(window_minutes=60, preset_name=preset_name)

    payload.update(
        {
            'session_active': bool(bootstrap_status.get('session_active')),
            'heartbeat_active': bool(bootstrap_status.get('heartbeat_active')),
            'current_session_status': str(bootstrap_status.get('current_session_status') or 'UNKNOWN'),
            'validation_status': str(validation.get('validation_status') or 'UNKNOWN'),
            'trend_status': str(trend.get('trend_status') or 'UNKNOWN'),
            'readiness_status': str(trend.get('readiness_status') or 'UNKNOWN'),
            'gate_status': str(gate.get('gate_status') or 'UNKNOWN'),
            'extended_run_status': 'ACTIVE' if bool(extended.get('extended_run_active')) else str(extended.get('gate_status') or 'INACTIVE'),
            'funnel_status': str(funnel.get('funnel_status') or 'UNKNOWN'),
            'handoff_summary': {
                'summary_window': f"rolling_{int(funnel.get('window_minutes') or 60)}m",
                'shortlisted_signals': int(funnel.get('shortlisted_signals') or 0),
                'handoff_candidates': int(funnel.get('handoff_candidates') or 0),
                'consensus_reviews': int(funnel.get('consensus_reviews') or 0),
                'prediction_candidates': int(funnel.get('prediction_candidates') or 0),
                'risk_decisions': int(funnel.get('risk_decisions') or 0),
                'paper_execution_candidates': int(funnel.get('paper_execution_candidates') or 0),
                'handoff_reason_codes': list(funnel.get('handoff_reason_codes') or []),
            },
            'shortlist_handoff_summary': dict(funnel.get('shortlist_handoff_summary') or {}),
            'market_link_summary': dict(funnel.get('market_link_summary') or {}),
            'market_link_examples': list(funnel.get('market_link_examples') or []),
            'consensus_alignment': dict(funnel.get('consensus_alignment') or {}),
            'attention_mode': str(attention.get('attention_mode') or 'UNKNOWN'),
            'portfolio_summary': _build_portfolio_summary(),
            'scan_summary': _build_scan_summary(scan_run=scan_run),
            'next_action_hint': str(gate.get('next_action_hint') or validation.get('next_action_hint') or 'Review test console log'),
            'reason_codes': list(dict.fromkeys(gate.get('reason_codes') or [])),
        }
    )


def _log_line_items(payload: dict[str, Any]) -> str:
    scan = payload.get('scan_summary') or {}
    portfolio = payload.get('portfolio_summary') or {}
    warnings = payload.get('warnings') or []
    errors = payload.get('errors') or []
    blockers = payload.get('blocker_summary') or []
    handoff_summary = payload.get('handoff_summary') or {}
    shortlist_handoff = payload.get('shortlist_handoff_summary') or {}
    market_link = payload.get('market_link_summary') or {}
    market_link_examples = payload.get('market_link_examples') or []
    consensus_alignment = payload.get('consensus_alignment') or {}

    lines = [
        '=== Mission Control Test Console Export ===',
        f"timestamp: {payload.get('timestamp')}",
        f"preset: {payload.get('preset_name')}",
        f"test_status: {payload.get('test_status')}",
        f"current_phase: {payload.get('current_phase')}",
        f"validation_status: {payload.get('validation_status')}",
        f"trial_status: {payload.get('trial_status')}",
        f"trend_status: {payload.get('trend_status')}",
        f"readiness_status: {payload.get('readiness_status')}",
        f"gate_status: {payload.get('gate_status')}",
        f"extended_run_status: {payload.get('extended_run_status')}",
        f"session_active: {payload.get('session_active')}",
        f"heartbeat_active: {payload.get('heartbeat_active')}",
        f"current_session_status: {payload.get('current_session_status')}",
        f"attention_mode: {payload.get('attention_mode')}",
        f"funnel_status: {payload.get('funnel_status')}",
        'handoff_summary:',
        f"  summary_window={handoff_summary.get('summary_window') or 'rolling_60m'}",
        (
            f"  shortlisted_signals={handoff_summary.get('shortlisted_signals', 0)} "
            f"handoff_candidates={handoff_summary.get('handoff_candidates', 0)} "
            f"consensus_reviews={handoff_summary.get('consensus_reviews', 0)} "
            f"prediction_candidates={handoff_summary.get('prediction_candidates', 0)} "
            f"risk_decisions={handoff_summary.get('risk_decisions', 0)} "
            f"paper_execution_candidates={handoff_summary.get('paper_execution_candidates', 0)}"
        ),
        f"  handoff_reason_codes={','.join(handoff_summary.get('handoff_reason_codes') or []) or 'none'}",
        'shortlist_handoff_summary:',
        (
            f"  shortlisted_signals={shortlist_handoff.get('shortlisted_signals', 0)} "
            f"handoff_attempted={shortlist_handoff.get('handoff_attempted', 0)} "
            f"handoff_created={shortlist_handoff.get('handoff_created', 0)} "
            f"handoff_blocked={shortlist_handoff.get('handoff_blocked', 0)}"
        ),
        f"  shortlist_handoff_reason_codes={','.join(shortlist_handoff.get('shortlist_handoff_reason_codes') or []) or 'none'}",
        (
            f"  shortlist_handoff_examples="
            f"{shortlist_handoff.get('shortlist_handoff_examples') or []}"
        ),
        'market_link_summary:',
        (
            f"  shortlisted_signals={market_link.get('shortlisted_signals', 0)} "
            f"market_link_attempted={market_link.get('market_link_attempted', 0)} "
            f"market_link_resolved={market_link.get('market_link_resolved', 0)} "
            f"market_link_missing={market_link.get('market_link_missing', 0)} "
            f"market_link_ambiguous={market_link.get('market_link_ambiguous', 0)}"
        ),
        f"  market_link_reason_codes={','.join(market_link.get('market_link_reason_codes') or []) or 'none'}",
        f"  market_link_examples={market_link_examples or []}",
        (
            f"  consensus_alignment=consensus_reviews={consensus_alignment.get('consensus_reviews', 0)} "
            f"shortlist_aligned={consensus_alignment.get('shortlist_aligned_consensus_reviews', 0)} "
            f"aligned_with_shortlist={consensus_alignment.get('consensus_aligned_with_shortlist', True)}"
        ),
        'scan_summary:',
        f"  summary_window={scan.get('summary_window') or 'latest_scan_run'}",
        f"  runs={scan.get('runs', 0)} rss_items={scan.get('rss_items', 0)} reddit_items={scan.get('reddit_items', 0)} x_items={scan.get('x_items', 0)}",
        f"  deduped_items={scan.get('deduped_items', 0)} clusters={scan.get('clusters', 0)} shortlisted_signals={scan.get('shortlisted_signals', 0)}",
        'portfolio_summary:',
        f"  cash={portfolio.get('cash')} equity={portfolio.get('equity')} realized_pnl={portfolio.get('realized_pnl')} unrealized_pnl={portfolio.get('unrealized_pnl')}",
        f"  open_positions={portfolio.get('open_positions')} recent_trades_count={portfolio.get('recent_trades_count')}",
        f"reason_codes: {', '.join(payload.get('reason_codes') or []) or 'none'}",
        f"blockers: {', '.join(blockers) or 'none'}",
        f"warnings: {len(warnings)}",
    ]
    for item in warnings:
        lines.append(f'  - {item}')
    lines.append(f'errors: {len(errors)}')
    for item in errors:
        lines.append(f'  - {item}')

    lines.append(f"next_action_hint: {payload.get('next_action_hint')}")
    lines.append(f"summary: {payload.get('summary')}")
    return '\n'.join(lines)


def start_test_console(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    now = timezone.now()
    payload: dict[str, Any] = {
        'timestamp': now,
        'started_at': now,
        'ended_at': None,
        'preset_name': target_preset,
        'test_status': TEST_STATUS_RUNNING,
        'current_phase': 'bootstrap',
        'trial_status': 'SKIPPED',
        'validation_status': 'UNKNOWN',
        'trend_status': 'UNKNOWN',
        'readiness_status': 'UNKNOWN',
        'gate_status': 'UNKNOWN',
        'extended_run_status': 'NOT_RUN',
        'session_active': False,
        'heartbeat_active': False,
        'current_session_status': 'UNKNOWN',
        'attention_mode': 'UNKNOWN',
        'funnel_status': 'UNKNOWN',
        'handoff_summary': {},
        'shortlist_handoff_summary': {},
        'consensus_alignment': {},
        'warnings': [],
        'errors': [],
        'blocker_summary': [],
        'reason_codes': [],
        'step_results': [],
        'next_action_hint': 'Running test console pipeline',
    }
    _set_state(status=payload)

    scan_run: SourceScanRun | None = None

    try:
        bootstrap_result = bootstrap_live_read_only_paper_session(preset_name=target_preset, auto_start_heartbeat=True, start_now=True)
        payload['step_results'].append({'phase': 'bootstrap', 'status': 'ok', 'result': bootstrap_result})
        if str(bootstrap_result.get('bootstrap_action')) in {'BLOCKED', 'FAILED'}:
            payload['warnings'].append(f"bootstrap action={bootstrap_result.get('bootstrap_action')}")

        payload['current_phase'] = 'scan'
        try:
            scan_run = run_scan_agent(triggered_by='mission_control_test_console')
            payload['step_results'].append(
                {
                    'phase': 'scan',
                    'status': 'ok',
                    'result': {
                        'run_id': scan_run.id,
                        'signal_count': scan_run.signal_count,
                        'deduped_item_count': scan_run.deduped_item_count,
                        'clustered_count': scan_run.clustered_count,
                    },
                }
            )
            if int(scan_run.signal_count or 0) <= 0:
                payload['warnings'].append('scan produced zero signals')
                payload['blocker_summary'].append('SCAN_ZERO_SIGNALS')
        except Exception as exc:  # pragma: no cover
            payload['warnings'].append(f'scan skipped/failed: {exc}')
            payload['step_results'].append({'phase': 'scan', 'status': 'warning', 'result': {'error': str(exc)}})

        payload['current_phase'] = 'consensus_review'
        shortlisted_count = 0
        if scan_run:
            shortlisted_count = scan_run.signals.filter(status=NarrativeSignalStatus.SHORTLISTED).count()
        else:
            shortlisted_count = NarrativeSignal.objects.filter(status=NarrativeSignalStatus.SHORTLISTED).count()
        if shortlisted_count > 0:
            try:
                consensus = run_consensus_review(triggered_by='mission_control_test_console')
                payload['step_results'].append(
                    {
                        'phase': 'consensus_review',
                        'status': 'ok',
                        'result': {
                            'consensus_run_id': consensus.id,
                            'considered_signal_count': consensus.considered_signal_count,
                        },
                    }
                )
            except Exception as exc:  # pragma: no cover
                payload['warnings'].append(f'consensus review failed: {exc}')
                payload['step_results'].append({'phase': 'consensus_review', 'status': 'warning', 'result': {'error': str(exc)}})
        else:
            payload['step_results'].append({'phase': 'consensus_review', 'status': 'skipped', 'result': {'reason': 'no_shortlisted_signals'}})

        payload['current_phase'] = 'trial'
        trial = run_live_paper_trial_run(preset_name=target_preset, heartbeat_passes=1)
        payload['trial_status'] = str(trial.get('trial_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'trial', 'status': 'ok', 'result': trial})

        payload['current_phase'] = 'validation'
        validation = build_live_paper_validation_digest(preset_name=target_preset)
        payload['validation_status'] = str(validation.get('validation_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'validation', 'status': 'ok', 'result': validation})

        payload['current_phase'] = 'trend'
        trend = build_live_paper_trial_trend_digest(limit=5, preset=target_preset)
        payload['trend_status'] = str(trend.get('trend_status') or 'UNKNOWN')
        payload['readiness_status'] = str(trend.get('readiness_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'trend', 'status': 'ok', 'result': trend})

        payload['current_phase'] = 'gate'
        gate = build_extended_paper_run_gate(preset_name=target_preset)
        payload['gate_status'] = str(gate.get('gate_status') or 'UNKNOWN')
        payload['reason_codes'] = list(dict.fromkeys(gate.get('reason_codes') or []))
        payload['step_results'].append({'phase': 'gate', 'status': 'ok', 'result': gate})
        if payload['gate_status'] == 'BLOCK':
            payload['blocker_summary'].append('GATE_BLOCKED')

        payload['current_phase'] = 'extended_run'
        if payload['gate_status'] in {GATE_ALLOW, GATE_ALLOW_WITH_CAUTION}:
            launch = launch_extended_paper_run(preset_name=target_preset)
            payload['extended_run_status'] = str(launch.get('launch_status') or 'UNKNOWN')
            payload['step_results'].append({'phase': 'extended_run', 'status': 'ok', 'result': launch})
        else:
            payload['extended_run_status'] = 'SKIPPED_GATE_BLOCKED'
            payload['step_results'].append({'phase': 'extended_run', 'status': 'skipped', 'result': {'reason': 'gate_blocked'}})

        payload['current_phase'] = 'finalize'
        _sync_operational_snapshot(payload=payload, preset_name=target_preset, scan_run=scan_run)

        has_errors = bool(payload['errors'])
        has_warnings = bool(payload['warnings'] or payload['blocker_summary'])
        if has_errors:
            payload['test_status'] = TEST_STATUS_FAILED
        elif payload.get('gate_status') == 'BLOCK':
            payload['test_status'] = TEST_STATUS_BLOCKED
        elif has_warnings:
            payload['test_status'] = TEST_STATUS_COMPLETED_WITH_WARNINGS
        else:
            payload['test_status'] = TEST_STATUS_COMPLETED
    except Exception as exc:
        payload['errors'].append(str(exc))
        payload['test_status'] = TEST_STATUS_FAILED
    finally:
        payload['ended_at'] = timezone.now()
        payload['summary'] = (
            f"{payload['test_status']}: phase={payload.get('current_phase')} trial={payload.get('trial_status')} "
            f"validation={payload.get('validation_status')} gate={payload.get('gate_status')}"
        )
        payload['text_export'] = _log_line_items(payload)
        _set_state(status=payload, log=payload, append_history=True)

    return payload


def stop_test_console(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    status_snapshot, _last_log, _history = _get_state_snapshot()

    runner_state = get_runner_state()
    runner_before = str(runner_state.runner_status)
    session = _find_active_preset_session(preset_name=target_preset)

    actions: list[str] = []
    warnings: list[str] = []

    if session and str(session.session_status) == AutonomousRuntimeSessionStatus.RUNNING:
        pause_session(session_id=session.id)
        actions.append(f'paused_session:{session.id}')
    elif session and str(session.session_status) == AutonomousRuntimeSessionStatus.PAUSED:
        actions.append(f'session_already_paused:{session.id}')
    else:
        warnings.append('no_reusable_autopilot_session_found')

    if runner_before == 'RUNNING':
        pause_runner()
        actions.append('paused_heartbeat_runner')
    else:
        warnings.append(f'heartbeat_not_running:{runner_before}')

    bootstrap_status = get_live_paper_bootstrap_status(preset_name=target_preset)
    stop_status = TEST_STATUS_STOPPED if actions else status_snapshot.get('test_status') or TEST_STATUS_IDLE

    payload = {
        **status_snapshot,
        'timestamp': timezone.now(),
        'preset_name': target_preset,
        'test_status': stop_status,
        'current_phase': 'finalize',
        'ended_at': timezone.now(),
        'session_active': bool(bootstrap_status.get('session_active')),
        'heartbeat_active': bool(bootstrap_status.get('heartbeat_active')),
        'current_session_status': str(bootstrap_status.get('current_session_status') or 'UNKNOWN'),
        'stop_actions': actions,
        'stop_warnings': warnings,
        'summary': (
            'Stop applied conservatively.' if actions else 'No explicit stop primitive was applied; reported current state only.'
        ),
        'next_action_hint': 'Run start again when ready for next V1 paper diagnostic cycle',
    }
    payload['text_export'] = _log_line_items(payload)
    _set_state(status=payload, log=payload, append_history=True)
    return payload


def get_test_console_status() -> dict[str, Any]:
    status_snapshot, _last_log, _history = _get_state_snapshot()
    return status_snapshot


def export_test_console_log(*, fmt: str = 'text') -> dict[str, Any] | str:
    _status, last_log, history = _get_state_snapshot()
    payload = last_log or {
        'timestamp': timezone.now(),
        'test_status': TEST_STATUS_IDLE,
        'summary': 'No test has been executed yet.',
        'history_size': len(history),
    }
    if fmt == 'json':
        return payload
    return str(payload.get('text_export') or _log_line_items(payload))
