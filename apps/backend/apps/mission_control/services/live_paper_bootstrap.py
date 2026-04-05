from __future__ import annotations

from dataclasses import dataclass

from apps.autonomous_trader.services import build_summary as build_autonomous_trader_summary
from apps.mission_control.models import AutonomousRunnerStatus, AutonomousRuntimeSession, AutonomousRuntimeSessionStatus
from apps.mission_control.services.session_heartbeat import get_runner_state, start_runner
from apps.mission_control.services.session_runtime import pause_session, resume_session, start_session
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.portfolio_governor.services import build_governance_summary
from apps.profile_manager.services import build_profile_governance_summary
from apps.real_market_ops.services import get_real_scope_payload
from apps.runtime_governor.models import RuntimeMode, RuntimeSetBy
from apps.runtime_governor.services import get_capabilities_for_current_mode, get_runtime_state, set_runtime_mode

PRESET_NAME = 'live_read_only_paper_conservative'
MARKET_DATA_MODE_REAL_READ_ONLY = 'REAL_READ_ONLY'
PAPER_EXECUTION_MODE_PAPER_ONLY = 'PAPER_ONLY'
PORTFOLIO_POSTURE_CONSERVATIVE = 'CONSERVATIVE'

BOOTSTRAP_ACTION_CREATED_AND_STARTED = 'CREATED_AND_STARTED'
BOOTSTRAP_ACTION_STARTED_EXISTING_SAFE_SESSION = 'STARTED_EXISTING_SAFE_SESSION'
BOOTSTRAP_ACTION_REUSED_EXISTING_SESSION = 'REUSED_EXISTING_SESSION'
BOOTSTRAP_ACTION_BLOCKED = 'BLOCKED'
BOOTSTRAP_ACTION_FAILED = 'FAILED'


@dataclass(frozen=True)
class LivePaperBootstrapPreset:
    name: str
    runtime_mode: str
    market_data_mode: str
    paper_execution_mode: str
    portfolio_posture: str
    session_profile_slug: str


LIVE_READ_ONLY_PAPER_CONSERVATIVE_PRESET = LivePaperBootstrapPreset(
    name=PRESET_NAME,
    runtime_mode=RuntimeMode.PAPER_ASSIST,
    market_data_mode=MARKET_DATA_MODE_REAL_READ_ONLY,
    paper_execution_mode=PAPER_EXECUTION_MODE_PAPER_ONLY,
    portfolio_posture=PORTFOLIO_POSTURE_CONSERVATIVE,
    session_profile_slug='conservative_quiet',
)

PRESETS = {
    PRESET_NAME: LIVE_READ_ONLY_PAPER_CONSERVATIVE_PRESET,
}


def _resolve_preset(name: str | None) -> LivePaperBootstrapPreset:
    return PRESETS.get((name or PRESET_NAME).strip(), LIVE_READ_ONLY_PAPER_CONSERVATIVE_PRESET)


def _session_matches_preset(*, session: AutonomousRuntimeSession, preset: LivePaperBootstrapPreset) -> bool:
    metadata = session.metadata or {}
    return (
        metadata.get('autopilot_preset_name') == preset.name
        and metadata.get('market_data_mode') == preset.market_data_mode
        and metadata.get('paper_execution_mode') == preset.paper_execution_mode
        and session.runtime_mode == preset.runtime_mode
    )


def _find_reusable_session(*, preset: LivePaperBootstrapPreset) -> AutonomousRuntimeSession | None:
    candidates = AutonomousRuntimeSession.objects.filter(
        session_status__in=[AutonomousRuntimeSessionStatus.RUNNING, AutonomousRuntimeSessionStatus.PAUSED],
    ).order_by('-updated_at', '-id')
    for session in candidates[:20]:
        if _session_matches_preset(session=session, preset=preset):
            return session
    return None


def _ensure_runtime_mode(*, preset: LivePaperBootstrapPreset) -> tuple[bool, list[str], str]:
    result = set_runtime_mode(
        requested_mode=preset.runtime_mode,
        set_by=RuntimeSetBy.SYSTEM,
        rationale='Bootstrap live read-only paper autopilot conservative preset.',
        metadata={
            'source': 'mission_control.live_paper_bootstrap',
            'preset_name': preset.name,
            'market_data_mode': preset.market_data_mode,
            'paper_execution_mode': preset.paper_execution_mode,
        },
    )
    decision = result['decision']
    reasons = list(decision.reasons or [])
    return decision.allowed, reasons, result['state'].current_mode


def _build_stack_snapshot() -> dict:
    runtime_state = get_runtime_state()
    runtime_caps = get_capabilities_for_current_mode()
    paper_account, _ = ensure_demo_account()
    return {
        'runtime_state': runtime_state.current_mode,
        'runtime_capabilities': runtime_caps,
        'portfolio_governor': build_governance_summary(),
        'profile_manager': build_profile_governance_summary(),
        'real_market_ops': get_real_scope_payload(),
        'autonomous_trader': build_autonomous_trader_summary(),
        'paper_trading': {
            'account_slug': paper_account.slug,
            'currency': paper_account.currency,
            'paper_only': True,
        },
    }


def bootstrap_live_read_only_paper_session(*, preset_name: str | None = None, auto_start_heartbeat: bool = True, start_now: bool = True) -> dict:
    preset = _resolve_preset(preset_name)

    try:
        allowed, reasons, runtime_mode = _ensure_runtime_mode(preset=preset)
        stack_snapshot = _build_stack_snapshot()
        runtime_caps = stack_snapshot['runtime_capabilities']

        if not allowed:
            summary = 'Bootstrap blocked by runtime governor constraints.'
            return {
                'preset_name': preset.name,
                'session_created': False,
                'session_started': False,
                'heartbeat_started': False,
                'runtime_mode': runtime_mode,
                'paper_execution_mode': preset.paper_execution_mode,
                'market_data_mode': preset.market_data_mode,
                'bootstrap_action': BOOTSTRAP_ACTION_BLOCKED,
                'session_id': None,
                'next_step_summary': 'Resolve runtime/safety constraints and retry bootstrap.',
                'bootstrap_summary': f"{summary} Reasons: {'; '.join(reasons) or 'unknown'}",
                'stack_snapshot': stack_snapshot,
            }

        if start_now and not runtime_caps.get('allow_continuous_loop', False):
            summary = 'Bootstrap blocked because continuous loop is disabled by active constraints.'
            return {
                'preset_name': preset.name,
                'session_created': False,
                'session_started': False,
                'heartbeat_started': False,
                'runtime_mode': runtime_mode,
                'paper_execution_mode': preset.paper_execution_mode,
                'market_data_mode': preset.market_data_mode,
                'bootstrap_action': BOOTSTRAP_ACTION_BLOCKED,
                'session_id': None,
                'next_step_summary': 'Inspect runtime governor, global mode enforcement, and safety guard status.',
                'bootstrap_summary': f"{summary} Reasons: {'; '.join(runtime_caps.get('blocked_reasons', [])) or 'allow_continuous_loop=false'}",
                'stack_snapshot': stack_snapshot,
            }

        reusable_session = _find_reusable_session(preset=preset)
        session_created = False
        session_started = False
        action = BOOTSTRAP_ACTION_REUSED_EXISTING_SESSION

        if reusable_session is None:
            metadata = {
                'autopilot_preset_name': preset.name,
                'market_data_mode': preset.market_data_mode,
                'paper_execution_mode': preset.paper_execution_mode,
                'portfolio_posture': preset.portfolio_posture,
                'bootstrap_source': 'mission_control.bootstrap-live-paper-session',
                'live_execution_enabled': False,
            }
            reusable_session = start_session(profile_slug=preset.session_profile_slug, runtime_mode=preset.runtime_mode)
            reusable_session.metadata = {**(reusable_session.metadata or {}), **metadata}
            reusable_session.save(update_fields=['metadata', 'updated_at'])
            session_created = True
            session_started = True
            action = BOOTSTRAP_ACTION_CREATED_AND_STARTED
            if not start_now:
                reusable_session = pause_session(session_id=reusable_session.id)
                session_started = False
        elif reusable_session.session_status == AutonomousRuntimeSessionStatus.PAUSED and start_now:
            reusable_session = resume_session(session_id=reusable_session.id)
            session_started = True
            action = BOOTSTRAP_ACTION_STARTED_EXISTING_SAFE_SESSION

        heartbeat_started = False
        runner_state = get_runner_state()
        if auto_start_heartbeat:
            if runner_state.runner_status != AutonomousRunnerStatus.RUNNING:
                runner_state = start_runner()
                heartbeat_started = True

        heartbeat_active = runner_state.runner_status == AutonomousRunnerStatus.RUNNING
        next_step_summary = (
            'Autopilot is active in live read-only paper mode; continue heartbeat supervision.'
            if heartbeat_active
            else 'Start heartbeat runner when ready to maintain autonomous cadence.'
        )

        return {
            'preset_name': preset.name,
            'session_created': session_created,
            'session_started': session_started,
            'heartbeat_started': heartbeat_started,
            'runtime_mode': runtime_mode,
            'paper_execution_mode': preset.paper_execution_mode,
            'market_data_mode': preset.market_data_mode,
            'bootstrap_action': action,
            'session_id': reusable_session.id,
            'next_step_summary': next_step_summary,
            'bootstrap_summary': (
                f"Bootstrap {action.lower()} with runtime={runtime_mode}, market_data={preset.market_data_mode}, "
                f"paper_execution={preset.paper_execution_mode}, heartbeat_active={heartbeat_active}."
            ),
            'stack_snapshot': stack_snapshot,
        }
    except Exception as exc:  # pragma: no cover - defensive fail-safe payload
        return {
            'preset_name': preset.name,
            'session_created': False,
            'session_started': False,
            'heartbeat_started': False,
            'runtime_mode': get_runtime_state().current_mode,
            'paper_execution_mode': preset.paper_execution_mode,
            'market_data_mode': preset.market_data_mode,
            'bootstrap_action': BOOTSTRAP_ACTION_FAILED,
            'session_id': None,
            'next_step_summary': 'Inspect mission_control bootstrap logs and retry once constraints are stable.',
            'bootstrap_summary': f'Bootstrap failed: {exc}',
        }


def get_live_paper_bootstrap_status(*, preset_name: str | None = None) -> dict:
    preset = _resolve_preset(preset_name)
    runtime_state = get_runtime_state()
    session = _find_reusable_session(preset=preset)
    runner_state = get_runner_state()
    session_active = bool(session and session.session_status == AutonomousRuntimeSessionStatus.RUNNING)
    heartbeat_active = runner_state.runner_status == AutonomousRunnerStatus.RUNNING

    if session is None:
        current_session_status = 'MISSING'
        operator_attention_hint = 'Bootstrap has not created a reusable session yet.'
    else:
        current_session_status = session.session_status
        operator_attention_hint = (
            'Session is paused; safe to resume with bootstrap POST.'
            if session.session_status == AutonomousRuntimeSessionStatus.PAUSED
            else 'Session is active; monitor heartbeat and safety guardrails.'
        )

    return {
        'preset_name': preset.name,
        'session_active': session_active,
        'heartbeat_active': heartbeat_active,
        'runtime_mode': runtime_state.current_mode,
        'market_data_mode': preset.market_data_mode,
        'paper_execution_mode': preset.paper_execution_mode,
        'current_session_status': current_session_status,
        'operator_attention_hint': operator_attention_hint,
        'status_summary': (
            f"preset={preset.name} session_active={session_active} heartbeat_active={heartbeat_active} "
            f"runtime_mode={runtime_state.current_mode} market_data_mode={preset.market_data_mode} "
            f"paper_execution_mode={preset.paper_execution_mode}"
        ),
    }
