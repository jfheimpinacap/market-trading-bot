from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import re
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone

from apps.autonomous_trader.models import (
    AutonomousDispatchMode,
    AutonomousDispatchRecord,
    AutonomousDispatchStatus,
    AutonomousExecutionStatus,
    AutonomousExecutionIntakeCandidate,
    AutonomousExecutionDecision,
    AutonomousExecutionDecisionStatus,
    AutonomousExecutionDecisionType,
    AutonomousExecutionIntakeRun,
    AutonomousExecutionIntakeStatus,
    AutonomousTradeCandidate,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
)
from apps.autonomous_trader.services.execution_intake.decision import decide_intake_candidate
from apps.autonomous_trader.services.execution_intake.intake import resolve_intake_status_from_readiness
from apps.autonomous_trader.services.execution_intake.run import run_execution_intake
from apps.markets.models import Market
from apps.mission_control.services.live_paper_bootstrap import PRESET_NAME
from apps.mission_control.services.live_paper_validation import build_live_paper_validation_digest
from apps.mission_control.services.session_heartbeat import build_heartbeat_summary
from apps.paper_trading.models import PaperTrade, PaperTradeStatus, PaperTradeType
from apps.paper_trading.services.execution import PaperTradingValidationError, execute_paper_trade
from apps.paper_trading.services.portfolio import build_account_summary, get_active_account
from apps.paper_trading.services.valuation import PaperTradingRejectionError
from apps.prediction_agent.models import PredictionConvictionReview, PredictionIntakeCandidate, PredictionIntakeRun, RiskReadyPredictionHandoff
from apps.prediction_agent.models import PredictionConvictionReviewStatus, PredictionIntakeStatus
from apps.prediction_agent.services.conviction import review_candidate
from apps.prediction_agent.services.risk_handoff import build_risk_ready_handoff
from apps.prediction_agent.services.run import run_prediction_intake_review
from apps.research_agent.models import NarrativeConsensusRecord
from apps.research_agent.models import MarketUniverseScanRun, NarrativeSignal, NarrativeSignalStatus, PredictionHandoffCandidate
from apps.research_agent.models import PredictionHandoffStatus, ResearchHandoffPriority, ResearchHandoffStatus, ResearchPursuitRun, ResearchStructuralAssessment
from apps.risk_agent.models import AutonomousExecutionReadiness, RiskApprovalDecision, RiskRuntimeApprovalStatus
from apps.risk_agent.services.run import run_risk_runtime_review

FUNNEL_ACTIVE = 'ACTIVE'
FUNNEL_THIN_FLOW = 'THIN_FLOW'
FUNNEL_STALLED = 'STALLED'

STAGE_ACTIVE = 'ACTIVE'
STAGE_LOW = 'LOW'
STAGE_EMPTY = 'EMPTY'

_LOW_THRESHOLD = 3
_MARKET_LINK_CONFIDENCE_THRESHOLD = Decimal('1.00')
_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD = Decimal('0.5500')
_PREDICTION_RISK_CAUTION_BAND_MIN = Decimal('0.4500')
_PREDICTION_RISK_CAUTION_BAND_MAX = Decimal('0.5500')
_PREDICTION_RISK_CAUTION_MIN_EDGE = Decimal('0.6500')
_BORDERLINE_CONFIDENCE_MIN = Decimal('0.4500')
_BORDERLINE_CONFIDENCE_MAX = Decimal('0.5500')
_BORDERLINE_MIN_NARRATIVE_PRIORITY = Decimal('0.7000')
_BORDERLINE_MIN_DIVERGENCE_STRENGTH = Decimal('0.6000')
_STRUCTURAL_ACTIVITY_MIN = Decimal('0.3000')
_STRUCTURAL_TIME_WINDOW_MIN = Decimal('0.2500')
_STRUCTURAL_ACTIVITY_EXTREME_MIN = Decimal('0.2000')
_STRUCTURAL_TIME_WINDOW_EXTREME_MIN = Decimal('0.2000')
_STRUCTURAL_OVERRIDE_MIN_VOLUME = Decimal('0.9000')
_STRUCTURAL_OVERRIDE_MIN_LIQUIDITY = Decimal('0.9000')
_STRUCTURAL_OVERRIDE_MIN_NARRATIVE = Decimal('0.8000')
_STRUCTURAL_OVERRIDE_MIN_DIVERGENCE = Decimal('0.6500')
_HANDOFF_SCORING_EXAMPLES_LIMIT = 3
_TOKEN_STOPWORDS = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'will', 'over'}
_DOWNSTREAM_ROUTE_NAME = 'research_pursuit_review'
_PREDICTION_INTAKE_ROUTE_NAME = 'prediction_intake_review'
_PREDICTION_RISK_ROUTE_NAME = 'risk_runtime_review'
_RISK_PAPER_EXECUTION_ROUTE_NAME = 'execution_intake'
_BORDERLINE_DECISION_SOURCE = 'mission_control_borderline_guardrail_v1'
_PREDICTION_STATUS_EXAMPLES_LIMIT = 3
_PREDICTION_RISK_CAUTION_EXAMPLES_LIMIT = 3
_PAPER_EXECUTION_VISIBILITY_EXAMPLES_LIMIT = 3
_PAPER_TRADE_EXAMPLES_LIMIT = 3
_EXECUTABLE_INTAKE_STATUSES = {
    AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
    AutonomousExecutionIntakeStatus.READY_REDUCED,
}


def _quantized(value: Decimal) -> str:
    return str(value.quantize(Decimal('0.0001')))


def _evaluate_structural_guardrail(*, handoff: PredictionHandoffCandidate, preset_name: str) -> dict[str, Any]:
    score_components = dict(getattr(getattr(handoff, 'linked_pursuit_score', None), 'score_components', {}) or {})
    structural_status = str(getattr(getattr(handoff, 'linked_assessment', None), 'structural_status', '') or '')
    activity_quality = _as_decimal(score_components.get('activity_quality'))
    time_window_quality = _as_decimal(score_components.get('time_window_quality'))
    volume_quality = _as_decimal(score_components.get('volume_quality'))
    liquidity_quality = _as_decimal(score_components.get('liquidity_quality'))
    narrative_priority = _as_decimal(score_components.get('narrative_priority'))
    divergence_strength = _as_decimal(score_components.get('divergence_strength'))

    weak_components: list[str] = []
    strong_components: list[str] = []
    component_rules = {
        'activity_quality': {'min': _quantized(_STRUCTURAL_ACTIVITY_MIN), 'extreme_min': _quantized(_STRUCTURAL_ACTIVITY_EXTREME_MIN)},
        'time_window_quality': {'min': _quantized(_STRUCTURAL_TIME_WINDOW_MIN), 'extreme_min': _quantized(_STRUCTURAL_TIME_WINDOW_EXTREME_MIN)},
        'override_strong_signals': {
            'min_volume_quality': _quantized(_STRUCTURAL_OVERRIDE_MIN_VOLUME),
            'min_liquidity_quality': _quantized(_STRUCTURAL_OVERRIDE_MIN_LIQUIDITY),
            'min_narrative_priority': _quantized(_STRUCTURAL_OVERRIDE_MIN_NARRATIVE),
            'min_divergence_strength': _quantized(_STRUCTURAL_OVERRIDE_MIN_DIVERGENCE),
        },
    }
    observed_values = {
        'activity_quality': _quantized(activity_quality),
        'time_window_quality': _quantized(time_window_quality),
        'volume_quality': _quantized(volume_quality),
        'liquidity_quality': _quantized(liquidity_quality),
        'narrative_priority': _quantized(narrative_priority),
        'divergence_strength': _quantized(divergence_strength),
    }
    structural_rule_type = 'aggregate'
    if activity_quality < _STRUCTURAL_ACTIVITY_MIN:
        weak_components.append('activity_quality')
    else:
        strong_components.append('activity_quality')
    if time_window_quality < _STRUCTURAL_TIME_WINDOW_MIN:
        weak_components.append('time_window_quality')
    else:
        strong_components.append('time_window_quality')
    if volume_quality >= _STRUCTURAL_OVERRIDE_MIN_VOLUME:
        strong_components.append('volume_quality')
    if liquidity_quality >= _STRUCTURAL_OVERRIDE_MIN_LIQUIDITY:
        strong_components.append('liquidity_quality')
    if narrative_priority >= _STRUCTURAL_OVERRIDE_MIN_NARRATIVE:
        strong_components.append('narrative_priority')
    if divergence_strength >= _STRUCTURAL_OVERRIDE_MIN_DIVERGENCE:
        strong_components.append('divergence_strength')

    has_extreme_weakness = activity_quality < _STRUCTURAL_ACTIVITY_EXTREME_MIN or time_window_quality < _STRUCTURAL_TIME_WINDOW_EXTREME_MIN
    strong_override_signals = (
        volume_quality >= _STRUCTURAL_OVERRIDE_MIN_VOLUME
        and liquidity_quality >= _STRUCTURAL_OVERRIDE_MIN_LIQUIDITY
        and narrative_priority >= _STRUCTURAL_OVERRIDE_MIN_NARRATIVE
        and divergence_strength >= _STRUCTURAL_OVERRIDE_MIN_DIVERGENCE
    )
    override_enabled = preset_name == PRESET_NAME and structural_status == 'deferred'
    override_applied = False

    if structural_status == 'prediction_ready':
        reason_code = 'HANDOFF_STRUCTURAL_PASS'
        blocked = False
        structural_rule_type = 'individual'
    elif structural_status not in {'deferred', 'blocked', 'watchlist_only'}:
        reason_code = 'HANDOFF_STRUCTURAL_WEAK_COMPOSITE'
        blocked = True
    elif 'activity_quality' in weak_components and 'time_window_quality' in weak_components:
        reason_code = 'HANDOFF_STRUCTURAL_WEAK_ACTIVITY_AND_TIME_WINDOW'
        blocked = True
    elif 'activity_quality' in weak_components:
        reason_code = 'HANDOFF_STRUCTURAL_WEAK_ACTIVITY'
        blocked = True
        structural_rule_type = 'individual'
    elif 'time_window_quality' in weak_components:
        reason_code = 'HANDOFF_STRUCTURAL_WEAK_TIME_WINDOW'
        blocked = True
        structural_rule_type = 'individual'
    else:
        reason_code = 'HANDOFF_STRUCTURAL_WEAK_COMPOSITE'
        blocked = True

    if blocked and override_enabled and not has_extreme_weakness and strong_override_signals:
        blocked = False
        override_applied = True
        reason_code = 'HANDOFF_STRUCTURAL_OVERRIDE_BORDERLINE'
        structural_rule_type = 'aggregate'

    structural_reason_code = reason_code
    if blocked:
        reason_code = 'HANDOFF_STRUCTURAL_BLOCK_BORDERLINE'

    return {
        'blocked': blocked,
        'reason_code': reason_code,
        'structural_reason_code': structural_reason_code,
        'structural_status': structural_status,
        'weak_components': weak_components,
        'strong_components': strong_components,
        'observed_values': observed_values,
        'thresholds': component_rules,
        'override_enabled': override_enabled,
        'override_applied': override_applied,
        'structural_rule_type': structural_rule_type,
        'decision_source': _BORDERLINE_DECISION_SOURCE,
    }


def _is_downstream_route_disabled() -> bool:
    return bool(getattr(settings, 'MISSION_CONTROL_DISABLE_RESEARCH_HANDOFF_ROUTE', False))


def _is_downstream_route_handler_available() -> bool:
    try:
        from apps.research_agent.services.pursuit_scoring.run import run_pursuit_review

        return callable(run_pursuit_review)
    except Exception:
        return False


def _is_prediction_intake_route_disabled() -> bool:
    return bool(getattr(settings, 'MISSION_CONTROL_DISABLE_PREDICTION_INTAKE_ROUTE', False))


def _is_prediction_intake_handler_available() -> bool:
    return callable(run_prediction_intake_review)


def _is_prediction_risk_route_disabled() -> bool:
    return bool(getattr(settings, 'MISSION_CONTROL_DISABLE_PREDICTION_RISK_ROUTE', False))


def _is_prediction_risk_handler_available() -> bool:
    return callable(run_risk_runtime_review)


def _is_paper_execution_route_disabled() -> bool:
    return bool(getattr(settings, 'MISSION_CONTROL_DISABLE_RISK_PAPER_EXECUTION_ROUTE', False))


def _is_paper_execution_handler_available() -> bool:
    return callable(run_execution_intake)


def _paper_execution_reason_from_risk_decision(*, approval_status: str, reason_codes: list[str], blocked_tags: set[str]) -> tuple[str, str]:
    if approval_status not in {RiskRuntimeApprovalStatus.APPROVED, RiskRuntimeApprovalStatus.APPROVED_REDUCED}:
        return 'PAPER_EXECUTION_STATUS_FILTER_REJECTED', 'risk_decision_status_filter'
    if 'POLICY' in blocked_tags:
        return 'PAPER_EXECUTION_BLOCKED_BY_POLICY', 'policy_gate'
    if 'SAFETY' in blocked_tags:
        return 'PAPER_EXECUTION_BLOCKED_BY_SAFETY', 'safety_gate'
    if 'RUNTIME' in blocked_tags:
        return 'PAPER_EXECUTION_BLOCKED_BY_RUNTIME', 'runtime_gate'
    if any(code == 'PREDICTION_RISK_ROUTE_MISSING' for code in reason_codes):
        return 'PAPER_EXECUTION_ARTIFACT_MISMATCH', 'risk_execution_artifact_adapter'
    return 'PAPER_EXECUTION_ROUTE_AVAILABLE', 'paper_execution_precheck'


def _is_visible_execution_intake_status(status_value: str) -> bool:
    return status_value in {
        AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
        AutonomousExecutionIntakeStatus.READY_REDUCED,
        AutonomousExecutionIntakeStatus.WATCH_ONLY,
    }


def _paper_trade_runtime_rejection_reason(error: Exception) -> tuple[str, str]:
    message = str(error or '').strip()
    lowered = message.lower()
    if 'insufficient' in lowered and 'cash' in lowered:
        return 'PAPER_TRADE_FINAL_BLOCKED_BY_CASH', message or 'insufficient_paper_cash'
    return 'PAPER_TRADE_FINAL_BLOCKED_BY_REJECTION', message or 'paper_runtime_rejection'


def _is_executable_execution_intake_status(status_value: str) -> bool:
    return status_value in _EXECUTABLE_INTAKE_STATUSES


def _candidate_lineage_key(*, candidate: AutonomousExecutionIntakeCandidate) -> tuple[Any, ...]:
    prediction_context = dict(getattr(candidate, 'linked_prediction_context', {}) or {})
    prediction_candidate_id = _safe_int(prediction_context.get('prediction_candidate_id') or prediction_context.get('linked_prediction_candidate_id'))
    handoff_id = _safe_int(prediction_context.get('handoff_id') or prediction_context.get('linked_handoff_id'))
    if prediction_candidate_id is not None or handoff_id is not None:
        ancestry_anchor = f'prediction:{prediction_candidate_id}|handoff:{handoff_id}'
    else:
        ancestry_anchor = f"approval:{_safe_int(getattr(candidate, 'linked_approval_review_id', None))}"
    return (
        _safe_int(getattr(candidate, 'linked_market_id', None)),
        ancestry_anchor,
        _safe_int(getattr(candidate, 'linked_sizing_plan_id', None)),
        _safe_int(getattr(candidate, 'linked_watch_plan_id', None)),
    )


def _dispatch_mode_for_decision(*, decision: AutonomousExecutionDecision) -> str:
    if decision.decision_type == AutonomousExecutionDecisionType.EXECUTE_REDUCED:
        return AutonomousDispatchMode.PAPER_REDUCED_EXECUTION
    return AutonomousDispatchMode.PAPER_EXECUTION


def _dispatch_status_for_decision(*, decision: AutonomousExecutionDecision) -> str:
    if decision.decision_type in {AutonomousExecutionDecisionType.BLOCK, AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW}:
        return AutonomousDispatchStatus.BLOCKED
    if decision.decision_type in {AutonomousExecutionDecisionType.KEEP_ON_WATCH, AutonomousExecutionDecisionType.DEFER}:
        return AutonomousDispatchStatus.SKIPPED
    return AutonomousDispatchStatus.QUEUED


def _is_reduce_or_exit_candidate(*, candidate: AutonomousExecutionIntakeCandidate, decision: AutonomousExecutionDecision) -> tuple[bool, str]:
    token_sources: list[str] = []
    token_sources.extend(str(code or '') for code in list(getattr(candidate, 'reason_codes', []) or []))
    token_sources.extend(str(code or '') for code in list(getattr(decision, 'reason_codes', []) or []))
    token_sources.extend(str(code or '') for code in list((getattr(decision, 'metadata', {}) or {}).get('reason_codes') or []))
    token_sources.append(str(getattr(candidate, 'execution_context_summary', '') or ''))
    portfolio_context = dict(getattr(candidate, 'linked_portfolio_context', {}) or {})
    token_sources.extend(str(value or '') for value in portfolio_context.values())
    token_blob = ' '.join(token_sources).upper()
    if any(token in token_blob for token in {'EXIT', 'CLOSE', 'CLOSING'}):
        return True, 'exit'
    if decision.decision_type == AutonomousExecutionDecisionType.EXECUTE_REDUCED:
        return True, 'reduce'
    if any(token in token_blob for token in {'REDUCE', 'DE-RISK', 'DERISK', 'TRIM'}):
        return True, 'reduce'
    return False, ''


@transaction.atomic
def _ensure_dispatch_records_for_candidates(
    *,
    candidates: list[AutonomousExecutionIntakeCandidate],
    decision_by_candidate_id: dict[int, AutonomousExecutionDecision],
    window_start,
) -> dict[str, Any]:
    if not candidates or not decision_by_candidate_id:
        return {
            'dispatch_by_candidate_id': {},
            'dispatch_created': 0,
            'dispatch_reused': 0,
            'dispatch_blocked': 0,
            'dispatch_dedupe_applied': 0,
            'reason_codes': [],
            'examples': [],
        }

    decision_ids = [int(decision.id) for decision in decision_by_candidate_id.values()]
    dispatch_rows = list(
        AutonomousDispatchRecord.objects.filter(linked_execution_decision_id__in=decision_ids)
        .select_related('linked_execution_decision', 'linked_execution_decision__linked_intake_candidate')
        .order_by('linked_execution_decision_id', '-created_at', '-id')
    )
    latest_dispatch_by_decision_id: dict[int, AutonomousDispatchRecord] = {}
    for row in dispatch_rows:
        decision_id = _safe_int(getattr(row, 'linked_execution_decision_id', None))
        if decision_id is not None and decision_id not in latest_dispatch_by_decision_id:
            latest_dispatch_by_decision_id[decision_id] = row

    lineage_dispatch_by_key: dict[tuple[Any, ...], AutonomousDispatchRecord] = {}
    for candidate in candidates:
        decision = decision_by_candidate_id.get(int(candidate.id))
        if decision is None:
            continue
        dispatch = latest_dispatch_by_decision_id.get(int(decision.id))
        if dispatch is not None:
            lineage_dispatch_by_key.setdefault(_candidate_lineage_key(candidate=candidate), dispatch)

    dispatch_by_candidate_id: dict[int, AutonomousDispatchRecord] = {}
    reason_codes: list[str] = []
    examples: list[dict[str, Any]] = []
    dispatch_created = 0
    dispatch_reused = 0
    dispatch_blocked = 0
    dispatch_dedupe_applied = 0

    for candidate in candidates:
        candidate_id = int(candidate.id)
        market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
        decision = decision_by_candidate_id.get(candidate_id)
        if decision is None:
            dispatch_blocked += 1
            reason_codes.append('PAPER_TRADE_DISPATCH_BLOCKED_BY_RUNTIME')
            continue
        lineage_key = _candidate_lineage_key(candidate=candidate)
        existing_dispatch = latest_dispatch_by_decision_id.get(int(decision.id))
        if existing_dispatch is not None:
            dispatch_by_candidate_id[candidate_id] = existing_dispatch
            lineage_dispatch_by_key.setdefault(lineage_key, existing_dispatch)
            dispatch_reused += 1
            reason_codes.extend(['PAPER_TRADE_DISPATCH_REUSED', 'PAPER_TRADE_DISPATCH_ROUTE_AVAILABLE'])
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'reason_code': 'PAPER_TRADE_DISPATCH_REUSED',
                        'blocking_stage': 'dispatch_record',
                        'observed_value': f'existing_dispatch_record:{existing_dispatch.id}',
                        'threshold': 'AutonomousDispatchRecord',
                    }
                )
            continue
        dedupe_dispatch = lineage_dispatch_by_key.get(lineage_key)
        if dedupe_dispatch is not None:
            dispatch_by_candidate_id[candidate_id] = dedupe_dispatch
            dispatch_reused += 1
            dispatch_dedupe_applied += 1
            reason_codes.extend(['PAPER_TRADE_DISPATCH_DEDUPE_REUSED', 'LINEAGE_DEDUPE_REUSED_EXISTING_DISPATCH', 'LINEAGE_DEDUPE_APPLIED'])
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'reason_code': 'PAPER_TRADE_DISPATCH_DEDUPE_REUSED',
                        'blocking_stage': 'dispatch_record_dedupe',
                        'observed_value': f'reused_dispatch_record:{dedupe_dispatch.id}',
                        'threshold': 'lineage/market dedupe key',
                    }
                )
            continue
        dispatch_status = _dispatch_status_for_decision(decision=decision)
        reason_hint = ''
        reason_code = 'PAPER_TRADE_DISPATCH_CREATED'
        if dispatch_status == AutonomousDispatchStatus.BLOCKED:
            if decision.decision_type == AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW:
                reason_hint = 'manual_review_required'
                reason_codes.append('PAPER_TRADE_DISPATCH_BLOCKED_BY_SAFETY')
            else:
                reason_hint = 'risk_or_policy_block'
                reason_codes.append('PAPER_TRADE_DISPATCH_BLOCKED_BY_POLICY')
        elif dispatch_status == AutonomousDispatchStatus.SKIPPED:
            reason_hint = 'deferred_or_watch_only'
        metadata = {
            'paper_only': True,
            'source': 'mission_control_dispatch_bridge',
            'decision_type': str(decision.decision_type or ''),
            'decision_status': str(decision.decision_status or AutonomousExecutionDecisionStatus.PROPOSED),
            'reason_hint': reason_hint,
        }
        created_dispatch = AutonomousDispatchRecord.objects.create(
            linked_execution_decision=decision,
            dispatch_status=dispatch_status,
            dispatch_mode=_dispatch_mode_for_decision(decision=decision),
            dispatch_summary='Paper-only dispatch bridge materialized dispatch record from execution decision.',
            metadata=metadata,
        )
        latest_dispatch_by_decision_id[int(decision.id)] = created_dispatch
        lineage_dispatch_by_key[lineage_key] = created_dispatch
        dispatch_by_candidate_id[candidate_id] = created_dispatch
        dispatch_created += 1
        reason_codes.extend([reason_code, 'PAPER_TRADE_DISPATCH_ROUTE_AVAILABLE'])
        if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
            examples.append(
                {
                    'execution_candidate_id': candidate_id,
                    'market_id': market_id,
                    'reason_code': reason_code,
                    'blocking_stage': 'dispatch_record_bridge',
                    'observed_value': f'created_dispatch_record:{created_dispatch.id}',
                    'threshold': 'AutonomousDispatchRecord',
                }
            )

    return {
        'dispatch_by_candidate_id': dispatch_by_candidate_id,
        'dispatch_created': int(dispatch_created),
        'dispatch_reused': int(dispatch_reused),
        'dispatch_blocked': int(dispatch_blocked),
        'dispatch_dedupe_applied': int(dispatch_dedupe_applied),
        'reason_codes': list(dict.fromkeys(reason_codes)),
        'examples': examples,
    }


@transaction.atomic
def _ensure_final_paper_trade_for_dispatches(
    *,
    candidates: list[AutonomousExecutionIntakeCandidate],
    decision_by_candidate_id: dict[int, AutonomousExecutionDecision],
    dispatch_by_candidate_id: dict[int, AutonomousDispatchRecord],
    window_start,
) -> dict[str, Any]:
    final_trade_by_candidate_id: dict[int, PaperTrade] = {}
    reason_codes: list[str] = []
    examples: list[dict[str, Any]] = []
    final_trade_created = 0
    final_trade_reused = 0
    final_trade_blocked = 0
    final_trade_deduped = 0
    dispatches_considered = 0
    dispatches_deduplicated = 0
    runtime_rejection_count = 0
    runtime_rejection_reason_codes: list[str] = []
    cash_available = Decimal('0')
    cash_budget_remaining = Decimal('0')
    selected_for_execution = 0
    blocked_by_cash_precheck = 0
    deferred_by_budget = 0
    blocked_by_active_position = 0
    allowed_without_exposure = 0
    allowed_for_exit = 0
    estimated_cash_selected = Decimal('0')
    cash_throttle_reason_codes: list[str] = []
    position_exposure_reason_codes: list[str] = []
    dedupe_trade_by_lineage_key: dict[tuple[Any, ...], PaperTrade] = {}
    dedupe_dispatch_by_lineage_key: dict[tuple[Any, ...], int] = {}

    if not candidates or not dispatch_by_candidate_id:
        return {
            'final_trade_by_candidate_id': final_trade_by_candidate_id,
            'final_trade_created': 0,
            'final_trade_reused': 0,
            'final_trade_blocked': 0,
            'final_trade_deduped': 0,
            'dispatches_considered': 0,
            'dispatches_deduplicated': 0,
            'runtime_rejection_count': 0,
            'runtime_rejection_reason_codes': [],
            'runtime_rejection_summary': 'runtime_rejection_count=0 runtime_rejection_reason_codes=none',
            'cash_available': 0.0,
            'cash_budget_remaining': 0.0,
            'selected_for_execution': 0,
            'blocked_by_cash_precheck': 0,
            'deferred_by_budget': 0,
            'blocked_by_active_position': 0,
            'allowed_without_exposure': 0,
            'allowed_for_exit': 0,
            'open_positions_detected': 0,
            'position_exposure_reason_codes': [],
            'estimated_cash_selected': 0.0,
            'cash_throttle_reason_codes': [],
            'cash_throttle_summary': (
                'cash_available=0.00 executable_candidates=0 selected_for_execution=0 '
                'blocked_by_cash_precheck=0 deferred_by_budget=0 estimated_cash_selected=0.00 '
                'cash_budget_remaining=0.00 cash_throttle_reason_codes=none'
            ),
            'reason_codes': [],
            'examples': [],
            'portfolio_exposure_context': {'open_positions': 0},
        }

    account = get_active_account()
    portfolio_summary = build_account_summary(account=account)
    cash_available = _as_decimal(portfolio_summary.get('cash_balance', portfolio_summary.get('cash', '0')))
    cash_budget_remaining = cash_available
    open_positions_by_market: set[int] = set()
    open_position_values = account.positions.filter(status='OPEN', quantity__gt=0).values_list('market_id', flat=True)
    try:
        open_positions_by_market = {
            int(market_id)
            for market_id in open_position_values
            if market_id is not None
        }
    except TypeError:
        open_positions_by_market = set()
    active_dispatch_lineages: set[tuple[Any, ...]] = set()
    if candidates:
        candidate_market_ids = list({_safe_int(getattr(candidate, 'linked_market_id', None)) for candidate in candidates if _safe_int(getattr(candidate, 'linked_market_id', None)) is not None})
        current_dispatch_ids = [int(dispatch.id) for dispatch in dispatch_by_candidate_id.values() if getattr(dispatch, 'id', None) is not None]
        if candidate_market_ids:
            active_dispatches = (
                AutonomousDispatchRecord.objects.filter(
                    linked_execution_decision__linked_intake_candidate__linked_market_id__in=candidate_market_ids,
                    dispatch_status__in=[
                        AutonomousDispatchStatus.QUEUED,
                        AutonomousDispatchStatus.DISPATCHED,
                        AutonomousDispatchStatus.PARTIAL,
                        AutonomousDispatchStatus.FILLED,
                    ],
                )
                .exclude(id__in=current_dispatch_ids)
                .select_related('linked_execution_decision__linked_intake_candidate')
                .order_by('-created_at', '-id')
            )
            for active_dispatch in active_dispatches:
                linked_candidate = getattr(getattr(active_dispatch, 'linked_execution_decision', None), 'linked_intake_candidate', None)
                if linked_candidate is None:
                    continue
                active_dispatch_lineages.add(_candidate_lineage_key(candidate=linked_candidate))

    for candidate in candidates:
        candidate_id = int(candidate.id)
        market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
        decision = decision_by_candidate_id.get(candidate_id)
        dispatch = dispatch_by_candidate_id.get(candidate_id)
        if dispatch is None or decision is None:
            continue
        dispatches_considered += 1
        dispatch_status = str(dispatch.dispatch_status or '')
        lineage_key = _candidate_lineage_key(candidate=candidate)
        if dispatch_status not in {AutonomousDispatchStatus.QUEUED, AutonomousDispatchStatus.DISPATCHED, AutonomousDispatchStatus.PARTIAL, AutonomousDispatchStatus.FILLED}:
            final_trade_blocked += 1
            if dispatch_status == AutonomousDispatchStatus.BLOCKED:
                if decision.decision_type == AutonomousExecutionDecisionType.BLOCK:
                    reason_code = 'PAPER_TRADE_FINAL_BLOCKED_BY_POLICY'
                elif decision.decision_type == AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW:
                    reason_code = 'PAPER_TRADE_FINAL_BLOCKED_BY_SAFETY'
                else:
                    reason_code = 'PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME'
            elif dispatch_status == AutonomousDispatchStatus.SKIPPED:
                reason_code = 'PAPER_TRADE_FINAL_BLOCKED_BY_POLICY'
            else:
                reason_code = 'PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME'
            reason_codes.append(reason_code)
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': _safe_int(dispatch.linked_paper_trade_id),
                        'reason_code': reason_code,
                        'blocking_stage': 'final_trade_status_gate',
                        'observed_value': dispatch_status,
                        'threshold': 'QUEUED|DISPATCHED|PARTIAL|FILLED',
                    }
                )
            continue

        if dispatch.linked_paper_trade_id:
            final_trade = dispatch.linked_paper_trade
            if final_trade is not None:
                final_trade_by_candidate_id[candidate_id] = final_trade
                final_trade_reused += 1
                reason_codes.append('PAPER_TRADE_FINAL_REUSED')
                dedupe_trade_by_lineage_key.setdefault(lineage_key, final_trade)
                if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                    examples.append(
                        {
                            'dispatch_id': int(dispatch.id),
                            'execution_candidate_id': candidate_id,
                            'market_id': market_id,
                            'dispatch_status': dispatch_status,
                            'linked_paper_trade_id': int(final_trade.id),
                            'reason_code': 'PAPER_TRADE_FINAL_REUSED',
                            'blocking_stage': 'final_trade_bridge',
                            'observed_value': f'existing_linked_paper_trade:{final_trade.id}',
                            'threshold': 'linked_paper_trade_id',
                        }
                    )
                continue

        dedupe_trade = dedupe_trade_by_lineage_key.get(lineage_key)
        if dedupe_trade is not None:
            dispatch.linked_paper_trade = dedupe_trade
            dispatch.dispatch_status = AutonomousDispatchStatus.DISPATCHED
            dispatch.metadata = {
                **dict(dispatch.metadata or {}),
                'paper_only': True,
                'final_trade_bridge': 'mission_control',
                'reason_code': 'PAPER_TRADE_FINAL_DEDUPE_REUSED',
            }
            dispatch.save(update_fields=['linked_paper_trade', 'dispatch_status', 'metadata', 'updated_at'])
            final_trade_by_candidate_id[candidate_id] = dedupe_trade
            final_trade_reused += 1
            final_trade_deduped += 1
            dispatches_deduplicated += 1
            reason_codes.extend(['PAPER_TRADE_FINAL_DEDUPE_REUSED', 'LINEAGE_DEDUPE_REUSED_EXISTING_TRADE', 'LINEAGE_DEDUPE_APPLIED'])
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': int(dedupe_trade.id),
                        'reason_code': 'PAPER_TRADE_FINAL_DEDUPE_REUSED',
                        'blocking_stage': 'final_trade_bridge_dedupe',
                        'observed_value': f'reused_trade:{dedupe_trade.id}',
                        'threshold': 'lineage/market dispatch dedupe key',
                    }
                )
            continue

        dedupe_dispatch_id = dedupe_dispatch_by_lineage_key.get(lineage_key)
        if dedupe_dispatch_id is not None and dedupe_dispatch_id != int(dispatch.id):
            final_trade_blocked += 1
            dispatches_deduplicated += 1
            reason_codes.extend(['LINEAGE_DEDUPE_BLOCKED_DUPLICATE', 'LINEAGE_DEDUPE_APPLIED'])
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': _safe_int(dispatch.linked_paper_trade_id),
                        'reason_code': 'LINEAGE_DEDUPE_BLOCKED_DUPLICATE',
                        'blocking_stage': 'final_trade_bridge_dedupe',
                        'observed_value': f'duplicate_dispatch_for_lineage:{dedupe_dispatch_id}',
                        'threshold': 'single active dispatch per lineage/market',
                    }
                )
            continue
        dedupe_dispatch_by_lineage_key[lineage_key] = int(dispatch.id)

        is_reduce_or_exit, reduce_or_exit_type = _is_reduce_or_exit_candidate(candidate=candidate, decision=decision)
        has_active_position = market_id in open_positions_by_market if market_id is not None else False
        has_active_trade = lineage_key in active_dispatch_lineages
        if not is_reduce_or_exit and (has_active_position or has_active_trade):
            final_trade_blocked += 1
            blocked_by_active_position += 1
            position_exposure_reason_codes.extend(
                [
                    'POSITION_EXPOSURE_GATE_APPLIED',
                    'PAPER_TRADE_POSITION_GATE_APPLIED',
                    'POSITION_EXPOSURE_ACTIVE_POSITION_PRESENT',
                    'PAPER_TRADE_SKIPPED_BY_POSITION_EXPOSURE',
                    'PAPER_TRADE_BLOCKED_BY_ACTIVE_POSITION',
                ]
            )
            reason_codes.extend(
                [
                    'PAPER_TRADE_POSITION_GATE_APPLIED',
                    'PAPER_TRADE_SKIPPED_BY_POSITION_EXPOSURE',
                    'PAPER_TRADE_BLOCKED_BY_ACTIVE_POSITION',
                ]
            )
            if has_active_trade:
                reason_codes.append('PAPER_TRADE_BLOCKED_BY_EXISTING_OPEN_TRADE')
                position_exposure_reason_codes.append('POSITION_EXPOSURE_EXISTING_OPEN_TRADE')
                position_exposure_reason_codes.append('PAPER_TRADE_BLOCKED_BY_EXISTING_OPEN_TRADE')
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': _safe_int(dispatch.linked_paper_trade_id),
                        'reason_code': 'PAPER_TRADE_BLOCKED_BY_ACTIVE_POSITION',
                        'blocking_stage': 'final_trade_position_gate',
                        'observed_value': f'active_position={has_active_position} active_trade={has_active_trade}',
                        'threshold': 'no active exposure for additive entries',
                    }
                )
            continue
        if is_reduce_or_exit:
            allowed_for_exit += 1
            if reduce_or_exit_type == 'exit':
                reason_codes.extend(['PAPER_TRADE_ALLOWED_EXIT_POSITION', 'PAPER_TRADE_POSITION_GATE_BYPASSED_FOR_EXIT'])
                position_exposure_reason_codes.extend(
                    ['POSITION_EXPOSURE_EXIT_ALLOWED', 'PAPER_TRADE_ALLOWED_EXIT_POSITION', 'PAPER_TRADE_POSITION_GATE_BYPASSED_FOR_EXIT']
                )
            else:
                reason_codes.extend(['PAPER_TRADE_ALLOWED_REDUCE_POSITION', 'PAPER_TRADE_POSITION_GATE_BYPASSED_FOR_EXIT'])
                position_exposure_reason_codes.extend(
                    ['POSITION_EXPOSURE_EXIT_ALLOWED', 'PAPER_TRADE_ALLOWED_REDUCE_POSITION', 'PAPER_TRADE_POSITION_GATE_BYPASSED_FOR_EXIT']
                )
        else:
            allowed_without_exposure += 1

        linked_readiness = candidate.linked_execution_readiness
        market_probability = Decimal('0.50')
        if linked_readiness and linked_readiness.linked_approval_review and linked_readiness.linked_approval_review.linked_candidate.market_probability:
            market_probability = linked_readiness.linked_approval_review.linked_candidate.market_probability
        price = max(Decimal('0.10'), min(Decimal('0.90'), market_probability))
        notional = Decimal('50.00')
        if candidate.linked_sizing_plan and candidate.linked_sizing_plan.paper_notional_size:
            notional = Decimal(candidate.linked_sizing_plan.paper_notional_size)
        if decision.decision_type == AutonomousExecutionDecisionType.EXECUTE_REDUCED:
            notional = (notional * Decimal('0.50')).quantize(Decimal('0.01'))
        quantity = (notional / price).quantize(Decimal('0.0001')) if price > 0 else Decimal('0.0000')
        if quantity <= 0:
            final_trade_blocked += 1
            reason_codes.append('PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME')
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': _safe_int(dispatch.linked_paper_trade_id),
                        'reason_code': 'PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME',
                        'blocking_stage': 'final_trade_bridge_quantity',
                        'observed_value': str(quantity),
                        'threshold': 'quantity>0',
                    }
                )
            continue
        estimated_cost = max(Decimal('0.00'), notional.quantize(Decimal('0.01')))
        if estimated_cost > cash_budget_remaining:
            final_trade_blocked += 1
            blocked_by_cash_precheck += 1
            deferred_by_budget += 1
            reason_codes.extend(
                [
                    'PAPER_TRADE_BLOCKED_BY_CASH_PRECHECK',
                    'PAPER_TRADE_DEFERRED_BY_CASH_BUDGET',
                    'PAPER_TRADE_FINAL_BLOCKED_BY_CASH',
                ]
            )
            cash_throttle_reason_codes.extend(
                [
                    'PAPER_TRADE_BLOCKED_BY_CASH_PRECHECK',
                    'PAPER_TRADE_DEFERRED_BY_CASH_BUDGET',
                    'PAPER_TRADE_FINAL_BLOCKED_BY_CASH',
                ]
            )
            if cash_budget_remaining <= Decimal('0.00'):
                reason_codes.append('PAPER_TRADE_CASH_BUDGET_EXHAUSTED')
                cash_throttle_reason_codes.append('PAPER_TRADE_CASH_BUDGET_EXHAUSTED')
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': _safe_int(dispatch.linked_paper_trade_id),
                        'reason_code': 'PAPER_TRADE_BLOCKED_BY_CASH_PRECHECK',
                        'blocking_stage': 'final_trade_cash_precheck',
                        'observed_value': (
                            f'estimated_cost={estimated_cost} cash_budget_remaining={cash_budget_remaining.quantize(Decimal("0.01"))}'
                        ),
                        'threshold': 'estimated_cost<=cash_budget_remaining',
                    }
                )
            continue
        selected_for_execution += 1
        estimated_cash_selected += estimated_cost
        cash_budget_remaining = max(Decimal('0.00'), (cash_budget_remaining - estimated_cost).quantize(Decimal('0.01')))
        reason_codes.append('PAPER_TRADE_SELECTED_FOR_EXECUTION')
        cash_throttle_reason_codes.append('PAPER_TRADE_SELECTED_FOR_EXECUTION')
        try:
            result = execute_paper_trade(
                market=candidate.linked_market,
                trade_type=PaperTradeType.BUY,
                side='YES',
                quantity=quantity,
                notes='mission control final paper-only dispatch bridge',
                metadata={
                    'paper_only': True,
                    'source': 'mission_control_final_dispatch_bridge',
                    'execution_candidate_id': candidate_id,
                    'dispatch_id': int(dispatch.id),
                },
                execution_price=price,
            )
        except PaperTradingValidationError:
            final_trade_blocked += 1
            reason_codes.append('PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME')
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': _safe_int(dispatch.linked_paper_trade_id),
                        'reason_code': 'PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME',
                        'blocking_stage': 'final_trade_bridge',
                        'observed_value': 'paper_trade_validation_error',
                        'threshold': 'paper runtime validation',
                    }
                )
            continue
        except PaperTradingRejectionError as error:
            final_trade_blocked += 1
            runtime_rejection_count += 1
            rejection_reason_code, observed_value = _paper_trade_runtime_rejection_reason(error)
            reason_codes.extend(
                [
                    rejection_reason_code,
                    'PAPER_TRADE_FINAL_RUNTIME_REJECTION_CAPTURED',
                    'PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME',
                ]
            )
            runtime_rejection_reason_codes.extend(
                [
                    rejection_reason_code,
                    'PAPER_TRADE_FINAL_RUNTIME_REJECTION_CAPTURED',
                ]
            )
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'dispatch_id': int(dispatch.id),
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'dispatch_status': dispatch_status,
                        'linked_paper_trade_id': _safe_int(dispatch.linked_paper_trade_id),
                        'reason_code': rejection_reason_code,
                        'blocking_stage': 'final_trade_bridge_runtime_rejection',
                        'observed_value': observed_value,
                        'threshold': 'paper runtime rejection captured',
                    }
                )
            continue

        cycle_run = candidate.intake_run.linked_cycle_run
        if cycle_run is None:
            cycle_run = AutonomousTradeCycleRun.objects.create(
                cycle_mode='FULL_AUTONOMOUS_PAPER_LOOP',
                metadata={'source': 'mission_control_final_dispatch_bridge', 'paper_only': True},
            )
            candidate.intake_run.linked_cycle_run = cycle_run
            candidate.intake_run.save(update_fields=['linked_cycle_run', 'updated_at'])

        trade_candidate = AutonomousTradeCandidate.objects.create(
            cycle_run=cycle_run,
            linked_market=candidate.linked_market,
            linked_risk_recommendation=None,
            candidate_status='EXECUTION_READY',
            adjusted_edge=Decimal('0.0000'),
            confidence=decision.decision_confidence,
            risk_posture=candidate.approval_status or 'UNKNOWN',
            metadata={'source': 'mission_control_final_dispatch_bridge', 'execution_candidate_id': candidate_id},
        )
        trade_decision = AutonomousTradeDecision.objects.create(
            linked_candidate=trade_candidate,
            decision_type='EXECUTE_PAPER_TRADE',
            decision_status='EXECUTED',
            rationale='Mission control final bridge materialized paper trade from queued dispatch.',
            reason_codes=['MISSION_CONTROL_FINAL_DISPATCH_BRIDGE'],
            metadata={'execution_decision_id': int(decision.id), 'dispatch_id': int(dispatch.id)},
        )
        trade_execution = AutonomousTradeExecution.objects.create(
            linked_candidate=trade_candidate,
            linked_decision=trade_decision,
            linked_paper_trade=result.trade,
            execution_status=AutonomousExecutionStatus.FILLED,
            sizing_summary=f'notional={notional} quantity={quantity} price={price}',
            watch_plan_summary=candidate.linked_watch_plan.review_interval_hint if candidate.linked_watch_plan else 'No watch plan attached.',
            metadata={'paper_only': True, 'source': 'mission_control_final_dispatch_bridge'},
        )
        dispatch.linked_paper_trade = result.trade
        dispatch.linked_trade_execution = trade_execution
        dispatch.dispatch_status = AutonomousDispatchStatus.DISPATCHED
        dispatch.metadata = {
            **dict(dispatch.metadata or {}),
            'paper_only': True,
            'final_trade_bridge': 'mission_control',
            'reason_code': 'PAPER_TRADE_FINAL_CREATED',
        }
        dispatch.save(update_fields=['linked_paper_trade', 'linked_trade_execution', 'dispatch_status', 'metadata', 'updated_at'])
        decision.decision_status = AutonomousExecutionDecisionStatus.APPLIED
        decision.save(update_fields=['decision_status', 'updated_at'])
        final_trade_by_candidate_id[candidate_id] = result.trade
        dedupe_trade_by_lineage_key[lineage_key] = result.trade
        final_trade_created += 1
        reason_codes.extend(['PAPER_TRADE_FINAL_CREATED', 'PAPER_TRADE_FINAL_ARTIFACT_MISMATCH_RESOLVED'])
        if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
            examples.append(
                {
                    'dispatch_id': int(dispatch.id),
                    'execution_candidate_id': candidate_id,
                    'market_id': market_id,
                    'dispatch_status': dispatch_status,
                    'linked_paper_trade_id': int(result.trade.id),
                    'reason_code': 'PAPER_TRADE_FINAL_CREATED',
                    'blocking_stage': 'final_trade_bridge',
                    'observed_value': f'created_trade:{result.trade.id}',
                    'threshold': 'linked_paper_trade_id',
                }
            )

    exposure_detected_count = len(open_positions_by_market)
    if exposure_detected_count == 0 and active_dispatch_lineages:
        exposure_detected_count = len(active_dispatch_lineages)
    if exposure_detected_count == 0 and blocked_by_active_position > 0:
        exposure_detected_count = 1
    if not position_exposure_reason_codes:
        position_exposure_reason_codes.append('POSITION_EXPOSURE_NONE')

    return {
        'final_trade_by_candidate_id': final_trade_by_candidate_id,
        'final_trade_created': int(final_trade_created),
        'final_trade_reused': int(final_trade_reused),
        'final_trade_blocked': int(final_trade_blocked),
        'final_trade_deduped': int(final_trade_deduped),
        'dispatches_considered': int(dispatches_considered),
        'dispatches_deduplicated': int(dispatches_deduplicated),
        'runtime_rejection_count': int(runtime_rejection_count),
        'runtime_rejection_reason_codes': list(dict.fromkeys(runtime_rejection_reason_codes)),
        'runtime_rejection_summary': (
            f"runtime_rejection_count={runtime_rejection_count} "
            f"runtime_rejection_reason_codes={','.join(list(dict.fromkeys(runtime_rejection_reason_codes))) or 'none'}"
        ),
        'cash_available': float(cash_available.quantize(Decimal('0.01'))),
        'cash_budget_remaining': float(cash_budget_remaining.quantize(Decimal('0.01'))),
        'selected_for_execution': int(selected_for_execution),
        'blocked_by_cash_precheck': int(blocked_by_cash_precheck),
        'deferred_by_budget': int(deferred_by_budget),
        'blocked_by_active_position': int(blocked_by_active_position),
        'allowed_without_exposure': int(allowed_without_exposure),
        'allowed_for_exit': int(allowed_for_exit),
        'open_positions_detected': int(exposure_detected_count),
        'active_dispatch_exposures_detected': int(len(active_dispatch_lineages)),
        'position_exposure_reason_codes': list(dict.fromkeys(position_exposure_reason_codes)),
        'estimated_cash_selected': float(estimated_cash_selected.quantize(Decimal('0.01'))),
        'cash_throttle_reason_codes': list(dict.fromkeys(cash_throttle_reason_codes)),
        'cash_throttle_summary': (
            f"cash_available={cash_available.quantize(Decimal('0.01'))} "
            f"executable_candidates={len(candidates)} "
            f"selected_for_execution={selected_for_execution} "
            f"blocked_by_cash_precheck={blocked_by_cash_precheck} "
            f"deferred_by_budget={deferred_by_budget} "
            f"estimated_cash_selected={estimated_cash_selected.quantize(Decimal('0.01'))} "
            f"cash_budget_remaining={cash_budget_remaining.quantize(Decimal('0.01'))} "
            f"cash_throttle_reason_codes={','.join(list(dict.fromkeys(cash_throttle_reason_codes))) or 'none'}"
        ),
        'reason_codes': list(dict.fromkeys(reason_codes)),
        'examples': examples,
        'portfolio_exposure_context': {
            'open_positions': int(portfolio_summary.get('open_positions') or 0),
            'open_positions_count': int(portfolio_summary.get('open_positions_count') or 0),
        },
    }


def _build_position_exposure_summary_from_final_trade_gate(
    *,
    final_trade_bridge: dict[str, Any],
    portfolio_summary: dict[str, Any] | None = None,
    dominant_blocking_gate: str = 'NONE',
) -> dict[str, Any]:
    portfolio_summary = portfolio_summary or {}
    portfolio_open_positions = int(
        portfolio_summary.get('open_positions')
        or portfolio_summary.get('open_positions_count')
        or 0
    )
    blocked_by_active_position = int(final_trade_bridge.get('blocked_by_active_position') or 0)
    allowed_for_exit = int(final_trade_bridge.get('allowed_for_exit') or 0)
    allowed_without_exposure = int(final_trade_bridge.get('allowed_without_exposure') or 0)
    active_dispatch_exposures_detected = int(final_trade_bridge.get('active_dispatch_exposures_detected') or 0)
    open_positions_detected = max(
        int(final_trade_bridge.get('open_positions_detected') or 0),
        portfolio_open_positions,
    )

    reason_codes = list(final_trade_bridge.get('position_exposure_reason_codes') or [])
    if blocked_by_active_position > 0:
        reason_codes.append('POSITION_EXPOSURE_GATE_APPLIED')
        if portfolio_open_positions > 0:
            reason_codes.append('POSITION_EXPOSURE_ACTIVE_POSITION_PRESENT')
        if active_dispatch_exposures_detected > 0:
            reason_codes.append('POSITION_EXPOSURE_EXISTING_OPEN_TRADE')
    if allowed_for_exit > 0:
        reason_codes.append('POSITION_EXPOSURE_EXIT_ALLOWED')
    if allowed_without_exposure > 0:
        reason_codes.append('POSITION_EXPOSURE_ALLOWED_WITHOUT_EXPOSURE')
    if not reason_codes:
        reason_codes.append('POSITION_EXPOSURE_NONE')

    return {
        'open_positions_detected': int(open_positions_detected),
        'active_dispatch_exposures_detected': int(active_dispatch_exposures_detected),
        'candidates_blocked_by_active_position': int(blocked_by_active_position),
        'candidates_allowed_for_exit': int(allowed_for_exit),
        'candidates_allowed_without_exposure': int(allowed_without_exposure),
        'position_exposure_reason_codes': list(dict.fromkeys(reason_codes)),
        'dominant_blocking_gate': dominant_blocking_gate,
    }


def _build_final_fanout_diagnostics(
    *,
    executable_candidates: list[AutonomousExecutionIntakeCandidate],
    dispatch_by_candidate_id: dict[int, AutonomousDispatchRecord],
    final_trade_by_candidate_id: dict[int, PaperTrade],
    trades_materialized: int,
    trades_reused: int,
    blocked_by_active_position: int = 0,
) -> dict[str, Any]:
    lineage_counters: dict[tuple[Any, ...], dict[str, Any]] = {}
    for candidate in executable_candidates:
        candidate_id = int(candidate.id)
        lineage_key = _candidate_lineage_key(candidate=candidate)
        market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
        entry = lineage_counters.setdefault(
            lineage_key,
            {
                'market_id': market_id,
                'lineage_key': str(lineage_key),
                'execution_candidate_count': 0,
                'dispatch_ids': set(),
                'trade_ids': set(),
            },
        )
        entry['execution_candidate_count'] += 1
        dispatch = dispatch_by_candidate_id.get(candidate_id)
        if dispatch is not None:
            entry['dispatch_ids'].add(int(dispatch.id))
        final_trade = final_trade_by_candidate_id.get(candidate_id)
        if final_trade is not None:
            entry['trade_ids'].add(int(final_trade.id))

    duplicate_execution_candidates = 0
    duplicate_dispatches = 0
    duplicate_trades = 0
    reason_codes: list[str] = []
    examples: list[dict[str, Any]] = []
    for entry in lineage_counters.values():
        dispatch_count = len(entry['dispatch_ids'])
        trade_count = len(entry['trade_ids'])
        entry_reason = 'FINAL_LINEAGE_FANOUT_OK'
        if entry['execution_candidate_count'] > 1:
            duplicate_execution_candidates += entry['execution_candidate_count'] - 1
            entry_reason = 'FINAL_LINEAGE_DUPLICATE_EXECUTION_CANDIDATES'
            reason_codes.append(entry_reason)
        if dispatch_count > 1:
            duplicate_dispatches += dispatch_count - 1
            entry_reason = 'FINAL_LINEAGE_DUPLICATE_DISPATCHES'
            reason_codes.append(entry_reason)
        if trade_count > 1:
            duplicate_trades += trade_count - 1
            entry_reason = 'FINAL_LINEAGE_DUPLICATE_TRADES'
            reason_codes.append(entry_reason)
        if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT and entry_reason != 'FINAL_LINEAGE_FANOUT_OK':
            examples.append(
                {
                    'market_id': entry['market_id'],
                    'lineage_key': entry['lineage_key'],
                    'execution_candidate_count': int(entry['execution_candidate_count']),
                    'dispatch_count': int(dispatch_count),
                    'trade_count': int(trade_count),
                    'reason_code': entry_reason,
                }
            )

    if trades_reused > 0:
        reason_codes.append('FINAL_LINEAGE_REUSE_EXPECTED')
    if trades_reused > max(3, trades_materialized * 3):
        reason_codes.append('FINAL_LINEAGE_REUSE_EXCESSIVE')

    unique_markets = {
        entry.get('market_id')
        for entry in lineage_counters.values()
        if entry.get('market_id') is not None
    }
    market_fanout_ratio_excessive = bool(
        unique_markets and (len(executable_candidates) / max(len(unique_markets), 1)) > 3
    )
    fanout_excessive = any(
        (
            duplicate_execution_candidates > 0,
            duplicate_dispatches > 0,
            duplicate_trades > 0,
            'FINAL_LINEAGE_REUSE_EXCESSIVE' in reason_codes,
            market_fanout_ratio_excessive,
        )
    )
    reason_codes.append('FINAL_LINEAGE_FANOUT_EXCESSIVE' if fanout_excessive else 'FINAL_LINEAGE_FANOUT_OK')
    normalized_codes = list(dict.fromkeys(reason_codes))
    if blocked_by_active_position > 0:
        normalized_codes = list(dict.fromkeys(normalized_codes + ['FINAL_LINEAGE_CONTAINED_BY_POSITION_GATE']))
    final_status = 'EXCESSIVE' if fanout_excessive else 'OK'
    lineage_count = len(lineage_counters)
    return {
        'final_lineage_count': int(lineage_count),
        'unique_market_lineages': int(lineage_count),
        'duplicate_execution_candidates': int(duplicate_execution_candidates),
        'duplicate_dispatches': int(duplicate_dispatches),
        'duplicate_trades': int(duplicate_trades),
        'lineages_suppressed_by_position_gate': int(blocked_by_active_position),
        'final_fanout_status': final_status,
        'final_fanout_reason_codes': normalized_codes,
        'final_fanout_examples': examples[:_PAPER_TRADE_EXAMPLES_LIMIT],
        'final_fanout_summary': (
            f"final_lineage_count={lineage_count} unique_market_lineages={lineage_count} "
            f"duplicate_execution_candidates={duplicate_execution_candidates} duplicate_dispatches={duplicate_dispatches} "
            f"duplicate_trades={duplicate_trades} final_fanout_status={final_status} "
            f"final_fanout_reason_codes={','.join(normalized_codes) or 'none'}"
        ),
    }


def _build_cash_pressure_diagnostics(
    *,
    executable_candidates: list[AutonomousExecutionIntakeCandidate],
    dispatch_by_candidate_id: dict[int, AutonomousDispatchRecord],
    final_trade_reason_codes: list[str],
    final_fanout_summary: dict[str, Any],
    final_trade_created: int,
    final_trade_reused: int,
    final_trade_bridge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final_trade_bridge = final_trade_bridge or {}
    cash_available = _as_decimal(final_trade_bridge.get('cash_available'))
    estimated_cash_required = Decimal('0')
    candidates_at_risk_by_cash = 0
    examples: list[dict[str, Any]] = []
    selected_for_execution = int(final_trade_bridge.get('selected_for_execution') or 0)
    blocked_by_cash_precheck = int(final_trade_bridge.get('blocked_by_cash_precheck') or 0)
    blocked_by_active_position = int(final_trade_bridge.get('blocked_by_active_position') or 0)
    deferred_by_budget = int(final_trade_bridge.get('deferred_by_budget') or 0)
    cash_budget_remaining = _as_decimal(final_trade_bridge.get('cash_budget_remaining'))
    cash_throttle_reason_codes = list(final_trade_bridge.get('cash_throttle_reason_codes') or [])
    if cash_available <= Decimal('0.00'):
        account = get_active_account()
        portfolio_summary = build_account_summary(account=account)
        cash_available = _as_decimal(portfolio_summary.get('cash_balance', portfolio_summary.get('cash', '0')))
    if cash_budget_remaining < Decimal('0.00'):
        cash_budget_remaining = Decimal('0.00')

    for candidate in executable_candidates:
        candidate_id = int(candidate.id)
        market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
        dispatch = dispatch_by_candidate_id.get(candidate_id)
        estimated_cost = Decimal('50.00')
        if dispatch is not None and getattr(dispatch, 'dispatched_notional', None):
            estimated_cost = _as_decimal(dispatch.dispatched_notional, default='50.00')
        elif candidate.linked_sizing_plan and candidate.linked_sizing_plan.paper_notional_size:
            estimated_cost = _as_decimal(candidate.linked_sizing_plan.paper_notional_size, default='50.00')

        estimated_cash_required += estimated_cost
        candidate_reason = 'CASH_PRESSURE_OK'
        candidate_status = str(candidate.intake_status or '')
        if estimated_cost > cash_available:
            candidates_at_risk_by_cash += 1
            candidate_reason = 'CASH_PRESSURE_INSUFFICIENT_FOR_ALL'
            candidate_status = 'BLOCKED_BY_CASH_PRESSURE'
        if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
            examples.append(
                {
                    'execution_candidate_id': candidate_id,
                    'market_id': market_id,
                    'candidate_status': candidate_status,
                    'estimated_cost': float(estimated_cost.quantize(Decimal('0.01'))),
                    'observed_cash': float(cash_available.quantize(Decimal('0.01'))),
                    'reason_code': candidate_reason,
                }
            )

    reason_codes: list[str] = []
    estimated_executable = len(executable_candidates)
    blocking_final_trades = 'PAPER_TRADE_FINAL_BLOCKED_BY_CASH' in final_trade_reason_codes
    fanout_excessive = str(final_fanout_summary.get('final_fanout_status') or 'UNKNOWN') == 'EXCESSIVE'
    if candidates_at_risk_by_cash == 0 and estimated_cash_required <= cash_available:
        status = 'OK'
        reason_codes.append('CASH_PRESSURE_OK')
    else:
        status = 'HIGH'
        reason_codes.append('CASH_PRESSURE_HIGH')
    if estimated_cash_required > cash_available:
        reason_codes.append('CASH_PRESSURE_INSUFFICIENT_FOR_ALL')
    if blocked_by_cash_precheck > 0:
        reason_codes.append('CASH_PRESSURE_PRECHECK_THROTTLED')
    if candidates_at_risk_by_cash > 0:
        reason_codes.append('CASH_PRESSURE_POTENTIAL_RISK_VISIBLE')
    if blocking_final_trades:
        reason_codes.append('CASH_PRESSURE_BLOCKING_FINAL_TRADES')
    if blocked_by_active_position > 0:
        reason_codes.append('CASH_PRESSURE_SECONDARY_TO_POSITION_GATE')
    if final_trade_reused > 0:
        reason_codes.append('CASH_PRESSURE_REUSE_EXPECTED')
    if fanout_excessive:
        reason_codes.append('CASH_PRESSURE_FANOUT_EXCESSIVE')

    normalized_codes = list(dict.fromkeys(reason_codes))
    return {
        'cash_available': float(cash_available.quantize(Decimal('0.01'))),
        'executable_candidates': int(estimated_executable),
        'estimated_cash_required': float(estimated_cash_required.quantize(Decimal('0.01'))),
        'candidates_at_risk_by_cash': int(candidates_at_risk_by_cash),
        'candidates_blocked_by_cash_precheck': int(blocked_by_cash_precheck),
        'candidates_blocked_by_active_position': int(blocked_by_active_position),
        'candidates_blocked_by_cash': int(blocked_by_cash_precheck),
        'candidates_reused': int(final_trade_reused),
        'selected_for_execution': int(selected_for_execution),
        'blocked_by_cash_precheck': int(blocked_by_cash_precheck),
        'deferred_by_budget': int(deferred_by_budget),
        'cash_budget_remaining': float(cash_budget_remaining.quantize(Decimal('0.01'))),
        'cash_throttle_reason_codes': list(dict.fromkeys(cash_throttle_reason_codes)),
        'cash_pressure_status': status,
        'cash_pressure_reason_codes': normalized_codes,
        'cash_pressure_summary': (
            f"cash_available={cash_available.quantize(Decimal('0.01'))} "
            f"executable_candidates={estimated_executable} "
            f"selected_for_execution={selected_for_execution} "
            f"blocked_by_cash_precheck={blocked_by_cash_precheck} "
            f"deferred_by_budget={deferred_by_budget} "
            f"estimated_cash_required={estimated_cash_required.quantize(Decimal('0.01'))} "
            f"candidates_at_risk_by_cash={candidates_at_risk_by_cash} "
            f"candidates_blocked_by_cash_precheck={blocked_by_cash_precheck} "
            f"candidates_blocked_by_active_position={blocked_by_active_position} "
            f"candidates_blocked_by_cash={blocked_by_cash_precheck} "
            f"candidates_reused={final_trade_reused} "
            f"created={final_trade_created} "
            f"cash_budget_remaining={cash_budget_remaining.quantize(Decimal('0.01'))} "
            f"cash_throttle_reason_codes={','.join(list(dict.fromkeys(cash_throttle_reason_codes))) or 'none'} "
            f"cash_pressure_status={status} "
            f"cash_pressure_reason_codes={','.join(normalized_codes) or 'none'}"
        ),
        'cash_pressure_examples': examples[:_PAPER_TRADE_EXAMPLES_LIMIT],
    }


@transaction.atomic
def _ensure_execution_decisions_for_candidates(
    *,
    candidates: list[AutonomousExecutionIntakeCandidate],
    window_start,
) -> dict[str, Any]:
    if not candidates:
        return {
            'decision_by_candidate_id': {},
            'duplicate_candidate_ids': set(),
            'decision_created': 0,
            'decision_reused': 0,
            'decision_blocked': 0,
            'decision_dedupe_applied': 0,
            'reason_codes': [],
            'examples': [],
            'considered_candidates': 0,
            'deduplicated_candidates': 0,
        }
    candidate_ids = [int(candidate.id) for candidate in candidates]
    decision_rows = list(
        AutonomousExecutionDecision.objects.filter(linked_intake_candidate_id__in=candidate_ids)
        .select_related('linked_intake_candidate')
        .order_by('linked_intake_candidate_id', '-created_at', '-id')
    )
    latest_decision_by_candidate: dict[int, AutonomousExecutionDecision] = {}
    for decision in decision_rows:
        candidate_id = _safe_int(getattr(decision, 'linked_intake_candidate_id', None))
        if candidate_id is not None and candidate_id not in latest_decision_by_candidate:
            latest_decision_by_candidate[candidate_id] = decision

    decision_by_candidate_id: dict[int, AutonomousExecutionDecision] = {}
    lineage_decision_by_key: dict[tuple[Any, ...], AutonomousExecutionDecision] = {}
    duplicate_candidate_ids: set[int] = set()
    reason_codes: list[str] = []
    examples: list[dict[str, Any]] = []
    decision_created = 0
    decision_reused = 0
    decision_blocked = 0
    decision_dedupe_applied = 0

    for candidate in candidates:
        candidate_id = int(candidate.id)
        lineage_key = _candidate_lineage_key(candidate=candidate)
        market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
        latest_decision = latest_decision_by_candidate.get(candidate_id)
        if latest_decision is not None:
            decision_by_candidate_id[candidate_id] = latest_decision
            lineage_decision_by_key.setdefault(lineage_key, latest_decision)
            decision_reused += 1
            reason_codes.append('PAPER_TRADE_DECISION_REUSED')
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'reason_code': 'PAPER_TRADE_DECISION_REUSED',
                        'blocking_stage': 'execution_decision',
                        'observed_value': f'existing_execution_decision:{latest_decision.id}',
                        'threshold': 'AutonomousExecutionDecision',
                    }
                )
            continue

        dedupe_decision = lineage_decision_by_key.get(lineage_key)
        if dedupe_decision is not None:
            duplicate_candidate_ids.add(candidate_id)
            decision_by_candidate_id[candidate_id] = dedupe_decision
            decision_reused += 1
            decision_dedupe_applied += 1
            reason_codes.extend(['PAPER_TRADE_DECISION_DEDUPE_REUSED', 'LINEAGE_DEDUPE_REUSED_EXISTING_DECISION'])
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'reason_code': 'PAPER_TRADE_DECISION_DEDUPE_REUSED',
                        'blocking_stage': 'execution_decision',
                        'observed_value': f'reused_execution_decision:{dedupe_decision.id}',
                        'threshold': 'lineage/market dedupe key',
                    }
                )
            continue

        try:
            created_decision = decide_intake_candidate(candidate=candidate)
        except Exception:
            decision_blocked += 1
            reason_codes.append('PAPER_TRADE_DECISION_BLOCKED_BY_RUNTIME')
            if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                examples.append(
                    {
                        'execution_candidate_id': candidate_id,
                        'market_id': market_id,
                        'reason_code': 'PAPER_TRADE_DECISION_BLOCKED_BY_RUNTIME',
                        'blocking_stage': 'execution_decision',
                        'observed_value': 'decision_bridge_exception',
                        'threshold': 'AutonomousExecutionDecision',
                    }
                )
            continue

        decision_by_candidate_id[candidate_id] = created_decision
        lineage_decision_by_key[lineage_key] = created_decision
        decision_created += 1
        reason_codes.extend(['PAPER_TRADE_DECISION_CREATED', 'PAPER_TRADE_DECISION_ROUTE_AVAILABLE'])
        if len(examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
            examples.append(
                {
                    'execution_candidate_id': candidate_id,
                    'market_id': market_id,
                    'reason_code': 'PAPER_TRADE_DECISION_CREATED',
                    'blocking_stage': 'execution_decision',
                    'observed_value': str(created_decision.decision_type or ''),
                    'threshold': 'AutonomousExecutionDecision',
                }
            )

    if duplicate_candidate_ids:
        reason_codes.extend(['LINEAGE_DEDUPE_APPLIED', 'LINEAGE_DEDUPE_BLOCKED_DUPLICATE'])
    return {
        'decision_by_candidate_id': decision_by_candidate_id,
        'duplicate_candidate_ids': duplicate_candidate_ids,
        'decision_created': int(decision_created),
        'decision_reused': int(decision_reused),
        'decision_blocked': int(decision_blocked),
        'decision_dedupe_applied': int(decision_dedupe_applied),
        'reason_codes': list(dict.fromkeys(reason_codes)),
        'examples': examples,
        'considered_candidates': int(len(candidate_ids)),
        'deduplicated_candidates': int(len(duplicate_candidate_ids)),
    }


@transaction.atomic
def _ensure_execution_candidates_for_readiness(*, readiness_rows: list[AutonomousExecutionReadiness]) -> dict[int, AutonomousExecutionIntakeCandidate]:
    if not readiness_rows:
        return {}
    readiness_ids = [int(readiness.id) for readiness in readiness_rows]
    existing_by_readiness_id: dict[int, AutonomousExecutionIntakeCandidate] = {}
    existing_rows = list(
        AutonomousExecutionIntakeCandidate.objects.filter(linked_execution_readiness_id__in=readiness_ids)
        .select_related('linked_execution_readiness', 'linked_approval_review', 'linked_market')
        .order_by('linked_execution_readiness_id', '-created_at', '-id')
    )
    for candidate in existing_rows:
        readiness_id = int(getattr(candidate, 'linked_execution_readiness_id', 0) or 0)
        if readiness_id and readiness_id not in existing_by_readiness_id:
            existing_by_readiness_id[readiness_id] = candidate

    missing_readiness = [readiness for readiness in readiness_rows if int(readiness.id) not in existing_by_readiness_id]
    if not missing_readiness:
        return existing_by_readiness_id

    intake_run = AutonomousExecutionIntakeRun.objects.create(
        started_at=timezone.now(),
        completed_at=timezone.now(),
        metadata={'source': 'mission_control_execution_artifact_bridge', 'paper_only': True, 'dispatch_enabled': False},
    )
    for readiness in missing_readiness:
        approval = readiness.linked_approval_review
        status, reason_codes, approval_status = resolve_intake_status_from_readiness(readiness=readiness)
        existing_by_readiness_id[int(readiness.id)] = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=readiness.linked_market,
            linked_execution_readiness=readiness,
            linked_approval_review=approval,
            linked_sizing_plan=readiness.linked_sizing_plan,
            linked_watch_plan=readiness.linked_watch_plan,
            linked_prediction_context=(approval.linked_candidate.metadata or {}) if approval else {},
            linked_portfolio_context=(approval.linked_candidate.linked_portfolio_context or {}) if approval else {},
            intake_status=status,
            readiness_confidence=readiness.readiness_confidence,
            approval_status=approval_status,
            sizing_method=readiness.linked_sizing_plan.sizing_mode if readiness.linked_sizing_plan else '',
            execution_context_summary=readiness.readiness_summary,
            reason_codes=reason_codes,
            metadata={
                'source': 'mission_control_execution_artifact_bridge',
                'paper_only': True,
                'dispatch_enabled': False,
                'readiness_status': readiness.readiness_status,
                'readiness_id': readiness.id,
            },
        )
    return existing_by_readiness_id


def _build_paper_execution_diagnostics(*, risk_rows: list[RiskApprovalDecision], window_start) -> dict[str, Any]:
    route_disabled = _is_paper_execution_route_disabled()
    route_handler_available = _is_paper_execution_handler_available()
    route_infra_available = not route_disabled and route_handler_available
    reason_codes: list[str] = []
    examples: list[dict[str, Any]] = []
    route_expected = 0
    route_available = 0
    route_attempted = 0
    route_created = 0
    route_reused = 0
    route_blocked = 0
    route_missing_status_count = 0
    visibility_created_count = 0
    visibility_reused_count = 0
    visibility_visible_count = 0
    visibility_hidden_count = 0
    visibility_reason_codes: list[str] = []
    visibility_examples: list[dict[str, Any]] = []
    latest_readiness_by_decision_id: dict[int, AutonomousExecutionReadiness] = {}
    latest_intake_by_readiness_id: dict[int, AutonomousExecutionIntakeCandidate] = {}
    latest_intake_by_decision_id: dict[int, AutonomousExecutionIntakeCandidate] = {}
    readiness_source_by_id: dict[int, str] = {}
    bridge_materialized_count = 0

    decision_ids = [int(decision.id) for decision in risk_rows]
    if decision_ids:
        readiness_rows = list(
            AutonomousExecutionReadiness.objects.filter(linked_approval_review_id__in=decision_ids)
            .select_related('linked_market', 'linked_approval_review')
            .order_by('linked_approval_review_id', '-created_at', '-id')
        )
        for readiness in readiness_rows:
            decision_id = int(getattr(readiness, 'linked_approval_review_id', 0) or 0)
            if decision_id and decision_id not in latest_readiness_by_decision_id:
                latest_readiness_by_decision_id[decision_id] = readiness
                readiness_source_by_id[int(readiness.id)] = 'created' if readiness.created_at >= window_start else 'reused'

        readiness_ids = [int(readiness.id) for readiness in latest_readiness_by_decision_id.values()]
        if readiness_ids:
            intake_rows = list(
                AutonomousExecutionIntakeCandidate.objects.filter(linked_execution_readiness_id__in=readiness_ids)
                .select_related('linked_execution_readiness', 'linked_approval_review', 'linked_market')
                .order_by('linked_execution_readiness_id', '-created_at', '-id')
            )
            for intake in intake_rows:
                readiness_id = int(getattr(intake, 'linked_execution_readiness_id', 0) or 0)
                if readiness_id and readiness_id not in latest_intake_by_readiness_id:
                    latest_intake_by_readiness_id[readiness_id] = intake
            missing_readiness_rows = [
                readiness for readiness in latest_readiness_by_decision_id.values() if int(readiness.id) not in latest_intake_by_readiness_id
            ]
            if missing_readiness_rows:
                bridged_candidates = _ensure_execution_candidates_for_readiness(readiness_rows=missing_readiness_rows)
                for readiness_id, candidate in bridged_candidates.items():
                    if readiness_id not in latest_intake_by_readiness_id:
                        latest_intake_by_readiness_id[readiness_id] = candidate
                        bridge_materialized_count += 1

        intake_by_decision_rows = list(
            AutonomousExecutionIntakeCandidate.objects.filter(linked_approval_review_id__in=decision_ids)
            .select_related('linked_execution_readiness', 'linked_approval_review', 'linked_market')
            .order_by('linked_approval_review_id', '-created_at', '-id')
        )
        for intake in intake_by_decision_rows:
            linked_decision_id = int(getattr(intake, 'linked_approval_review_id', 0) or 0)
            if linked_decision_id and linked_decision_id not in latest_intake_by_decision_id:
                latest_intake_by_decision_id[linked_decision_id] = intake

    for decision in risk_rows:
        decision_id = int(decision.id)
        readiness: AutonomousExecutionReadiness | None = None
        market_id = _safe_int(getattr(decision.linked_candidate, 'linked_market_id', None))
        approval_status = str(decision.approval_status or '')
        decision_reason_codes = [str(code or '') for code in list(decision.reason_codes or []) if str(code or '').strip()]
        metadata_reason_codes = [str(code or '') for code in list((decision.metadata or {}).get('reason_codes') or []) if str(code or '').strip()]
        merged_reason_codes = list(dict.fromkeys(decision_reason_codes + metadata_reason_codes))
        blocked_tags = {tag for tag in {'POLICY', 'SAFETY', 'RUNTIME'} if any(tag in code.upper() for code in merged_reason_codes)}
        expected_route = _RISK_PAPER_EXECUTION_ROUTE_NAME if approval_status in {RiskRuntimeApprovalStatus.APPROVED, RiskRuntimeApprovalStatus.APPROVED_REDUCED} else None

        reason_code, blocking_stage = _paper_execution_reason_from_risk_decision(
            approval_status=approval_status,
            reason_codes=merged_reason_codes,
            blocked_tags=blocked_tags,
        )
        observed_value: Any = approval_status
        threshold: Any = f'{RiskRuntimeApprovalStatus.APPROVED}|{RiskRuntimeApprovalStatus.APPROVED_REDUCED}'

        if expected_route is None:
            route_missing_status_count += 1
            route_blocked += 1
            reason_codes.append(reason_code)
        elif not route_infra_available:
            route_expected += 1
            route_blocked += 1
            if route_disabled:
                reason_code = 'PAPER_EXECUTION_ROUTE_MISSING'
                blocking_stage = 'paper_execution_route'
                observed_value = 'route_disabled'
            else:
                reason_code = 'PAPER_EXECUTION_NO_ELIGIBLE_HANDLER'
                blocking_stage = 'paper_execution_handler'
                observed_value = 'handler_unavailable'
            threshold = _RISK_PAPER_EXECUTION_ROUTE_NAME
            reason_codes.append(reason_code)
        else:
            route_expected += 1
            route_available += 1
            reason_codes.append('PAPER_EXECUTION_ROUTE_AVAILABLE')
            readiness = latest_readiness_by_decision_id.get(decision_id)
            if readiness is not None:
                route_attempted += 1
                if readiness.created_at >= window_start:
                    route_created += 1
                    reason_code = 'PAPER_EXECUTION_CREATED'
                else:
                    route_reused += 1
                    reason_code = 'PAPER_EXECUTION_REUSED_EXISTING_CANDIDATE'
                blocking_stage = 'paper_execution_readiness'
                observed_value = str(readiness.readiness_status or '')
                threshold = 'READY|READY_REDUCED'
                reason_codes.append(reason_code)
            else:
                route_blocked += 1
                reason_code = 'PAPER_EXECUTION_ROUTE_MISSING'
                blocking_stage = 'paper_execution_readiness'
                observed_value = 'missing_readiness_artifact'
                threshold = 'AutonomousExecutionReadiness'
                reason_codes.append(reason_code)

        if len(examples) < 3:
            examples.append(
                {
                    'risk_decision_id': decision_id,
                    'market_id': market_id,
                    'decision_status': approval_status,
                    'expected_route': expected_route,
                    'reason_code': reason_code,
                    'blocking_stage': blocking_stage,
                    'observed_value': observed_value,
                    'threshold': threshold,
                }
            )
        if readiness is None:
            continue

        visibility_source = 'created' if readiness.created_at >= window_start else 'reused'
        if visibility_source == 'created':
            visibility_created_count += 1
        else:
            visibility_reused_count += 1
        intake_candidate = latest_intake_by_readiness_id.get(int(readiness.id))
        source_model = 'AutonomousExecutionIntakeCandidate'
        source_stage = 'execution_intake'
        status_value = ''
        visibility_window = 'current_window' if visibility_source == 'created' else 'outside_window_reused'
        visible_in_funnel = False
        visibility_reason_code = ''
        expected_artifact = 'AutonomousExecutionIntakeCandidate'
        created_artifact = visibility_source == 'created'
        reused_artifact = visibility_source == 'reused'
        execution_candidate_source = 'reused'
        if intake_candidate is not None and str((intake_candidate.metadata or {}).get('source') or '') == 'mission_control_execution_artifact_bridge':
            execution_candidate_source = 'created'

        if intake_candidate is None:
            intake_candidate = latest_intake_by_decision_id.get(decision_id)
            if intake_candidate is None:
                source_model = 'AutonomousExecutionReadiness'
                source_stage = 'risk_execution_readiness'
                visibility_reason_code = 'PAPER_EXECUTION_CANDIDATE_SOURCE_MODEL_MISMATCH'
            else:
                source_model = 'AutonomousExecutionIntakeCandidate'
                source_stage = 'execution_intake'
                status_value = str(intake_candidate.intake_status or '')
                if intake_candidate.created_at < window_start:
                    visibility_reason_code = 'PAPER_EXECUTION_CANDIDATE_HIDDEN_BY_WINDOW'
                elif _is_visible_execution_intake_status(status_value):
                    visible_in_funnel = True
                    visibility_reason_code = 'PAPER_EXECUTION_VISIBLE_IN_FUNNEL'
                else:
                    visibility_reason_code = 'PAPER_EXECUTION_CANDIDATE_HIDDEN_BY_STATUS'
        else:
            status_value = str(intake_candidate.intake_status or '')
            if intake_candidate.created_at < window_start:
                visibility_reason_code = 'PAPER_EXECUTION_CANDIDATE_HIDDEN_BY_WINDOW'
            elif _is_visible_execution_intake_status(status_value):
                visible_in_funnel = True
                visibility_reason_code = 'PAPER_EXECUTION_VISIBLE_IN_FUNNEL'
            else:
                visibility_reason_code = 'PAPER_EXECUTION_CANDIDATE_HIDDEN_BY_STATUS'

        if not visible_in_funnel and visibility_reason_code == 'PAPER_EXECUTION_CANDIDATE_SOURCE_MODEL_MISMATCH':
            visibility_reason_codes.append(visibility_reason_code)
            visibility_reason_codes.append(
                'PAPER_EXECUTION_CREATED_BUT_NOT_COUNTED' if visibility_source == 'created' else 'PAPER_EXECUTION_REUSED_BUT_NOT_COUNTED'
            )
        else:
            visibility_reason_codes.append(visibility_reason_code)

        if visible_in_funnel:
            visibility_visible_count += 1
        else:
            visibility_hidden_count += 1

        if len(visibility_examples) < _PAPER_EXECUTION_VISIBILITY_EXAMPLES_LIMIT:
            visibility_examples.append(
                {
                    'execution_candidate_id': _safe_int(getattr(intake_candidate, 'id', None)),
                    'risk_decision_id': decision_id,
                    'market_id': market_id,
                    'source': visibility_source,
                    'source_model': source_model,
                    'source_stage': source_stage,
                    'visible_in_funnel': bool(visible_in_funnel),
                    'reason_code': visibility_reason_code,
                    'visibility_window': visibility_window,
                    'status': status_value or str(readiness.readiness_status or ''),
                }
            )
        if visible_in_funnel and visibility_reason_code == 'PAPER_EXECUTION_VISIBLE_IN_FUNNEL':
            visibility_reason_codes.append('PAPER_EXECUTION_ARTIFACT_MISMATCH_RESOLVED')
        elif visibility_reason_code in {'PAPER_EXECUTION_CANDIDATE_SOURCE_MODEL_MISMATCH', 'PAPER_EXECUTION_CANDIDATE_HIDDEN_BY_STATUS', 'PAPER_EXECUTION_CANDIDATE_HIDDEN_BY_WINDOW'}:
            visibility_reason_codes.append('PAPER_EXECUTION_ARTIFACT_MISMATCH_BLOCKED')

        artifact_reason_code = (
            'PAPER_EXECUTION_CANDIDATE_CREATED'
            if execution_candidate_source == 'created'
            else ('PAPER_EXECUTION_CANDIDATE_REUSED' if intake_candidate is not None else 'PAPER_EXECUTION_ARTIFACT_MISMATCH_BLOCKED')
        )
        visibility_reason_codes.append(artifact_reason_code)
        visibility_reason_codes.append(
            'PAPER_EXECUTION_READINESS_CREATED' if readiness_source_by_id.get(int(readiness.id)) == 'created' else 'PAPER_EXECUTION_READINESS_REUSED'
        )
        if len(examples) < 3:
            examples.append(
                {
                    'readiness_id': int(readiness.id),
                    'risk_decision_id': decision_id,
                    'market_id': market_id,
                    'source_model': source_model,
                    'expected_artifact': expected_artifact,
                    'created_artifact': bool(created_artifact),
                    'reused_artifact': bool(reused_artifact),
                    'visible_in_funnel': bool(visible_in_funnel),
                    'reason_code': visibility_reason_code or artifact_reason_code,
                    'blocking_stage': 'execution_intake_visibility',
                }
            )

    normalized_codes = list(dict.fromkeys(reason_codes))
    normalized_visibility_codes = list(dict.fromkeys([code for code in visibility_reason_codes if code]))
    execution_readiness_created = sum(1 for source in readiness_source_by_id.values() if source == 'created')
    execution_readiness_reused = sum(1 for source in readiness_source_by_id.values() if source == 'reused')
    execution_candidate_created = sum(
        1
        for candidate in latest_intake_by_readiness_id.values()
        if str((candidate.metadata or {}).get('source') or '') == 'mission_control_execution_artifact_bridge' and candidate.created_at >= window_start
    )
    execution_candidate_reused = max(0, len(latest_intake_by_readiness_id) - execution_candidate_created)
    execution_artifact_blocked_count = max(0, len(latest_readiness_by_decision_id) - visibility_visible_count)
    execution_examples = visibility_examples[:3]
    visible_candidate_ids: list[int] = []
    for intake_candidate in latest_intake_by_decision_id.values():
        status_value = str(getattr(intake_candidate, 'intake_status', '') or '')
        if intake_candidate.created_at >= window_start and _is_visible_execution_intake_status(status_value):
            visible_candidate_ids.append(int(intake_candidate.id))
    visible_candidate_ids = list(dict.fromkeys(visible_candidate_ids))
    visible_candidates = list(
        AutonomousExecutionIntakeCandidate.objects.filter(id__in=visible_candidate_ids)
        .select_related('linked_market')
        .order_by('-created_at', '-id')
    )
    candidate_by_id = {int(candidate.id): candidate for candidate in visible_candidates}
    executable_candidate_ids: list[int] = []
    paper_trade_route_reason_codes: list[str] = []
    paper_trade_examples: list[dict[str, Any]] = []
    paper_trade_route_expected = int(len(visible_candidate_ids))
    paper_trade_route_available = int(len(visible_candidate_ids)) if route_infra_available else 0
    paper_trade_route_attempted = 0
    paper_trade_route_created = 0
    paper_trade_route_reused = 0
    paper_trade_route_blocked = 0
    paper_trade_decision_created = 0
    paper_trade_decision_reused = 0
    paper_trade_decision_blocked = 0
    paper_trade_decision_dedupe_applied = 0
    paper_trade_decision_reason_codes: list[str] = []
    paper_trade_decision_examples: list[dict[str, Any]] = []
    paper_trade_dispatch_created = 0
    paper_trade_dispatch_reused = 0
    paper_trade_dispatch_blocked = 0
    paper_trade_dispatch_dedupe_applied = 0
    paper_trade_dispatch_reason_codes: list[str] = []
    paper_trade_dispatch_examples: list[dict[str, Any]] = []
    final_trade_expected = 0
    final_trade_available = 0
    final_trade_attempted = 0
    final_trade_created = 0
    final_trade_reused = 0
    final_trade_blocked = 0
    final_trade_reason_codes: list[str] = []
    final_trade_examples: list[dict[str, Any]] = []
    runtime_rejection_count = 0
    runtime_rejection_reason_codes: list[str] = []
    final_trade_cash_available = Decimal('0.00')
    final_trade_cash_budget_remaining = Decimal('0.00')
    final_trade_selected_for_execution = 0
    final_trade_blocked_by_cash_precheck = 0
    final_trade_deferred_by_budget = 0
    final_trade_blocked_by_active_position = 0
    final_trade_allowed_without_exposure = 0
    final_trade_allowed_for_exit = 0
    open_positions_detected = 0
    position_exposure_reason_codes: list[str] = []
    final_trade_cash_throttle_reason_codes: list[str] = []
    dispatches_considered = 0
    dispatches_deduplicated = 0
    execution_lineage_considered = 0
    execution_lineage_deduplicated = 0
    promotion_suppressed_by_active_position = 0
    promotion_suppressed_by_existing_open_trade = 0
    promotion_allowed_for_exit = 0
    promotion_allowed_without_exposure = 0
    promotion_gate_reason_codes: list[str] = []
    promotion_gate_examples: list[dict[str, Any]] = []
    executable_candidates: list[AutonomousExecutionIntakeCandidate] = []
    latest_decision_by_candidate: dict[int, AutonomousExecutionDecision] = {}
    duplicate_candidate_ids: set[int] = set()
    latest_dispatch_by_candidate: dict[int, AutonomousDispatchRecord] = {}
    final_trade_map: dict[int, PaperTrade] = {}
    final_trade_bridge: dict[str, Any] = {}

    if not route_infra_available and paper_trade_route_expected > 0:
        reason = 'PAPER_TRADE_ROUTE_MISSING' if route_disabled else 'PAPER_TRADE_NO_ELIGIBLE_HANDLER'
        paper_trade_route_reason_codes.append(reason)
        paper_trade_route_blocked = int(paper_trade_route_expected)
        for candidate_id in visible_candidate_ids[:_PAPER_TRADE_EXAMPLES_LIMIT]:
            candidate = candidate_by_id.get(candidate_id)
            if candidate is None:
                continue
            paper_trade_examples.append(
                {
                    'execution_candidate_id': int(candidate.id),
                    'market_id': _safe_int(getattr(candidate, 'linked_market_id', None)),
                    'candidate_status': str(candidate.intake_status or ''),
                    'expected_route': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                    'reason_code': reason,
                    'blocking_stage': 'paper_trade_route',
                    'observed_value': 'route_disabled' if route_disabled else 'handler_unavailable',
                    'threshold': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                }
            )

    if route_infra_available and visible_candidate_ids:
        for candidate_id in visible_candidate_ids:
            candidate = candidate_by_id.get(candidate_id)
            if candidate is None:
                continue
            market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
            candidate_status = str(candidate.intake_status or '')
            if _is_executable_execution_intake_status(candidate_status):
                executable_candidate_ids.append(int(candidate.id))
            else:
                paper_trade_route_blocked += 1
                paper_trade_route_reason_codes.append('PAPER_TRADE_STATUS_FILTER_REJECTED')
                if len(paper_trade_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                    paper_trade_examples.append(
                        {
                            'execution_candidate_id': int(candidate.id),
                            'market_id': market_id,
                            'candidate_status': candidate_status,
                            'expected_route': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                            'reason_code': 'PAPER_TRADE_STATUS_FILTER_REJECTED',
                            'blocking_stage': 'candidate_status',
                            'observed_value': candidate_status,
                            'threshold': '|'.join(sorted(_EXECUTABLE_INTAKE_STATUSES)),
                        }
                    )

        if executable_candidate_ids:
            executable_candidates = [candidate_by_id[candidate_id] for candidate_id in executable_candidate_ids if candidate_id in candidate_by_id]
            promotion_gate_candidates: list[AutonomousExecutionIntakeCandidate] = []
            if executable_candidates:
                account = get_active_account()
                open_positions_by_market: set[int] = set()
                open_position_values = account.positions.filter(status='OPEN', quantity__gt=0).values_list('market_id', flat=True)
                try:
                    open_positions_by_market = {
                        int(market_id)
                        for market_id in open_position_values
                        if market_id is not None
                    }
                except TypeError:
                    open_positions_by_market = set()
                active_dispatch_candidate_ids_by_lineage: dict[tuple[Any, ...], set[int]] = {}
                existing_dispatch_candidate_ids = set(
                    AutonomousDispatchRecord.objects.filter(
                        linked_execution_decision__linked_intake_candidate_id__in=executable_candidate_ids
                    ).values_list('linked_execution_decision__linked_intake_candidate_id', flat=True)
                )
                candidate_market_ids = list(
                    {
                        _safe_int(getattr(candidate, 'linked_market_id', None))
                        for candidate in executable_candidates
                        if _safe_int(getattr(candidate, 'linked_market_id', None)) is not None
                    }
                )
                if candidate_market_ids:
                    active_dispatches = (
                        AutonomousDispatchRecord.objects.filter(
                            linked_execution_decision__linked_intake_candidate__linked_market_id__in=candidate_market_ids,
                            dispatch_status__in=[
                                AutonomousDispatchStatus.QUEUED,
                                AutonomousDispatchStatus.DISPATCHED,
                                AutonomousDispatchStatus.PARTIAL,
                                AutonomousDispatchStatus.FILLED,
                            ],
                        )
                        .select_related('linked_execution_decision__linked_intake_candidate')
                        .order_by('-created_at', '-id')
                    )
                    for active_dispatch in active_dispatches:
                        linked_candidate = getattr(getattr(active_dispatch, 'linked_execution_decision', None), 'linked_intake_candidate', None)
                        if linked_candidate is None:
                            continue
                        active_lineage_key = _candidate_lineage_key(candidate=linked_candidate)
                        linked_candidate_id = _safe_int(getattr(linked_candidate, 'id', None))
                        if linked_candidate_id is None:
                            continue
                        active_dispatch_candidate_ids_by_lineage.setdefault(active_lineage_key, set()).add(linked_candidate_id)
                for candidate in executable_candidates:
                    market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
                    candidate_lineage_key = _candidate_lineage_key(candidate=candidate)
                    if int(candidate.id) in existing_dispatch_candidate_ids:
                        promotion_allowed_without_exposure += 1
                        promotion_gate_reason_codes.append('EXECUTION_PROMOTION_ALLOWED_WITHOUT_EXPOSURE')
                        promotion_gate_candidates.append(candidate)
                        continue
                    token_sources: list[str] = []
                    token_sources.extend(str(code or '') for code in list(getattr(candidate, 'reason_codes', []) or []))
                    token_sources.append(str(getattr(candidate, 'execution_context_summary', '') or ''))
                    portfolio_context = dict(getattr(candidate, 'linked_portfolio_context', {}) or {})
                    token_sources.extend(str(value or '') for value in portfolio_context.values())
                    token_blob = ' '.join(token_sources).upper()
                    reduce_or_exit = str(getattr(candidate, 'intake_status', '') or '') == AutonomousExecutionIntakeStatus.READY_REDUCED or any(
                        token in token_blob for token in {'EXIT', 'CLOSE', 'CLOSING', 'REDUCE', 'DE-RISK', 'DERISK', 'TRIM'}
                    )
                    if not reduce_or_exit:
                        has_active_position = market_id in open_positions_by_market if market_id is not None else False
                        active_candidate_ids = active_dispatch_candidate_ids_by_lineage.get(candidate_lineage_key, set())
                        has_active_trade = any(existing_id != int(candidate.id) for existing_id in active_candidate_ids)
                        if has_active_position:
                            promotion_suppressed_by_active_position += 1
                            promotion_gate_reason_codes.append('EXECUTION_PROMOTION_SUPPRESSED_BY_ACTIVE_POSITION')
                            if len(promotion_gate_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                                promotion_gate_examples.append(
                                    {
                                        'execution_candidate_id': int(candidate.id),
                                        'market_id': market_id,
                                        'candidate_status': str(getattr(candidate, 'intake_status', '') or ''),
                                        'reason_code': 'EXECUTION_PROMOTION_SUPPRESSED_BY_ACTIVE_POSITION',
                                        'promotion_outcome': 'suppressed',
                                        'exposure_gate': 'active_position',
                                    }
                                )
                        elif has_active_trade:
                            promotion_suppressed_by_existing_open_trade += 1
                            promotion_gate_reason_codes.append('EXECUTION_PROMOTION_SUPPRESSED_BY_EXISTING_OPEN_TRADE')
                            if len(promotion_gate_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                                promotion_gate_examples.append(
                                    {
                                        'execution_candidate_id': int(candidate.id),
                                        'market_id': market_id,
                                        'candidate_status': str(getattr(candidate, 'intake_status', '') or ''),
                                        'reason_code': 'EXECUTION_PROMOTION_SUPPRESSED_BY_EXISTING_OPEN_TRADE',
                                        'promotion_outcome': 'suppressed',
                                        'exposure_gate': 'existing_open_trade',
                                    }
                                )
                        else:
                            promotion_allowed_without_exposure += 1
                            promotion_gate_reason_codes.append('EXECUTION_PROMOTION_ALLOWED_WITHOUT_EXPOSURE')
                            promotion_gate_candidates.append(candidate)
                            if len(promotion_gate_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                                promotion_gate_examples.append(
                                    {
                                        'execution_candidate_id': int(candidate.id),
                                        'market_id': market_id,
                                        'candidate_status': str(getattr(candidate, 'intake_status', '') or ''),
                                        'reason_code': 'EXECUTION_PROMOTION_ALLOWED_WITHOUT_EXPOSURE',
                                        'promotion_outcome': 'promoted',
                                        'exposure_gate': 'clear',
                                    }
                                )
                        continue
                    promotion_allowed_for_exit += 1
                    promotion_gate_reason_codes.append('EXECUTION_PROMOTION_ALLOWED_FOR_EXIT')
                    promotion_gate_candidates.append(candidate)
                    if len(promotion_gate_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                        promotion_gate_examples.append(
                            {
                                'execution_candidate_id': int(candidate.id),
                                'market_id': market_id,
                                'candidate_status': str(getattr(candidate, 'intake_status', '') or ''),
                                'reason_code': 'EXECUTION_PROMOTION_ALLOWED_FOR_EXIT',
                                'promotion_outcome': 'promoted',
                                'exposure_gate': 'exit_or_reduce',
                            }
                        )
            executable_candidates = promotion_gate_candidates
            decision_bridge = _ensure_execution_decisions_for_candidates(candidates=executable_candidates, window_start=window_start)
            latest_decision_by_candidate = dict(decision_bridge.get('decision_by_candidate_id') or {})
            duplicate_candidate_ids = set(decision_bridge.get('duplicate_candidate_ids') or set())
            paper_trade_decision_created = int(decision_bridge.get('decision_created') or 0)
            paper_trade_decision_reused = int(decision_bridge.get('decision_reused') or 0)
            paper_trade_decision_blocked = int(decision_bridge.get('decision_blocked') or 0)
            paper_trade_decision_dedupe_applied = int(decision_bridge.get('decision_dedupe_applied') or 0)
            paper_trade_decision_reason_codes.extend(list(decision_bridge.get('reason_codes') or []))
            paper_trade_decision_examples.extend(list(decision_bridge.get('examples') or []))
            execution_lineage_considered = int(decision_bridge.get('considered_candidates') or 0)
            execution_lineage_deduplicated = int(decision_bridge.get('deduplicated_candidates') or 0)
            dispatch_bridge = _ensure_dispatch_records_for_candidates(
                candidates=executable_candidates,
                decision_by_candidate_id=latest_decision_by_candidate,
                window_start=window_start,
            )
            latest_dispatch_by_candidate = dict(dispatch_bridge.get('dispatch_by_candidate_id') or {})
            paper_trade_dispatch_created = int(dispatch_bridge.get('dispatch_created') or 0)
            paper_trade_dispatch_reused = int(dispatch_bridge.get('dispatch_reused') or 0)
            paper_trade_dispatch_blocked = int(dispatch_bridge.get('dispatch_blocked') or 0)
            paper_trade_dispatch_dedupe_applied = int(dispatch_bridge.get('dispatch_dedupe_applied') or 0)
            paper_trade_dispatch_reason_codes.extend(list(dispatch_bridge.get('reason_codes') or []))
            paper_trade_dispatch_examples.extend(list(dispatch_bridge.get('examples') or []))
            final_trade_bridge = _ensure_final_paper_trade_for_dispatches(
                candidates=executable_candidates,
                decision_by_candidate_id=latest_decision_by_candidate,
                dispatch_by_candidate_id=latest_dispatch_by_candidate,
                window_start=window_start,
            )
            final_trade_map = dict(final_trade_bridge.get('final_trade_by_candidate_id') or {})
            final_trade_created = int(final_trade_bridge.get('final_trade_created') or 0)
            final_trade_reused = int(final_trade_bridge.get('final_trade_reused') or 0)
            final_trade_blocked = int(final_trade_bridge.get('final_trade_blocked') or 0)
            final_trade_reason_codes.extend(list(final_trade_bridge.get('reason_codes') or []))
            final_trade_examples.extend(list(final_trade_bridge.get('examples') or []))
            dispatches_considered = int(final_trade_bridge.get('dispatches_considered') or 0)
            dispatches_deduplicated = int(final_trade_bridge.get('dispatches_deduplicated') or 0)
            runtime_rejection_count = int(final_trade_bridge.get('runtime_rejection_count') or 0)
            runtime_rejection_reason_codes.extend(list(final_trade_bridge.get('runtime_rejection_reason_codes') or []))
            final_trade_cash_available = _as_decimal(final_trade_bridge.get('cash_available'))
            final_trade_cash_budget_remaining = _as_decimal(final_trade_bridge.get('cash_budget_remaining'))
            final_trade_selected_for_execution = int(final_trade_bridge.get('selected_for_execution') or 0)
            final_trade_blocked_by_cash_precheck = int(final_trade_bridge.get('blocked_by_cash_precheck') or 0)
            final_trade_deferred_by_budget = int(final_trade_bridge.get('deferred_by_budget') or 0)
            final_trade_blocked_by_active_position = int(final_trade_bridge.get('blocked_by_active_position') or 0)
            final_trade_allowed_without_exposure = int(final_trade_bridge.get('allowed_without_exposure') or 0)
            final_trade_allowed_for_exit = int(final_trade_bridge.get('allowed_for_exit') or 0)
            open_positions_detected = int(final_trade_bridge.get('open_positions_detected') or 0)
            position_exposure_reason_codes.extend(list(final_trade_bridge.get('position_exposure_reason_codes') or []))
            final_trade_cash_throttle_reason_codes.extend(list(final_trade_bridge.get('cash_throttle_reason_codes') or []))
            final_trade_expected = int(len(executable_candidates))
            final_trade_available = int(sum(1 for dispatch in latest_dispatch_by_candidate.values() if dispatch is not None))
            final_trade_attempted = int(final_trade_selected_for_execution or dispatches_considered)

            for candidate in executable_candidates:
                candidate_id = int(candidate.id)
                market_id = _safe_int(getattr(candidate, 'linked_market_id', None))
                if candidate_id in duplicate_candidate_ids:
                    paper_trade_route_blocked += 1
                    paper_trade_route_reason_codes.append('LINEAGE_DEDUPE_BLOCKED_DUPLICATE')
                    if len(paper_trade_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                        paper_trade_examples.append(
                            {
                                'execution_candidate_id': int(candidate.id),
                                'market_id': market_id,
                                'candidate_status': str(candidate.intake_status or ''),
                                'expected_route': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                                'reason_code': 'LINEAGE_DEDUPE_BLOCKED_DUPLICATE',
                                'blocking_stage': 'execution_decision_dedupe',
                                'observed_value': 'duplicate_lineage_market_candidate',
                                'threshold': 'single active decision per lineage/market',
                            }
                        )
                    continue
                decision = latest_decision_by_candidate.get(candidate_id)
                if decision is None:
                    paper_trade_route_blocked += 1
                    paper_trade_route_reason_codes.append('PAPER_TRADE_BLOCKED_BY_RUNTIME')
                    paper_trade_decision_reason_codes.append('PAPER_TRADE_DECISION_BLOCKED_BY_RUNTIME')
                    paper_trade_dispatch_reason_codes.append('PAPER_TRADE_DISPATCH_BLOCKED_BY_RUNTIME')
                    if len(paper_trade_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                        paper_trade_examples.append(
                            {
                                'execution_candidate_id': int(candidate.id),
                                'market_id': market_id,
                                'candidate_status': str(candidate.intake_status or ''),
                                'expected_route': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                                'reason_code': 'PAPER_TRADE_BLOCKED_BY_RUNTIME',
                                'blocking_stage': 'execution_decision',
                                'observed_value': 'missing_execution_decision',
                                'threshold': 'AutonomousExecutionDecision',
                            }
                        )
                    continue
                paper_trade_route_attempted += 1
                dispatch = latest_dispatch_by_candidate.get(candidate_id)
                if dispatch is None:
                    paper_trade_route_blocked += 1
                    paper_trade_route_reason_codes.append('PAPER_TRADE_BLOCKED_BY_RUNTIME')
                    paper_trade_dispatch_reason_codes.append('PAPER_TRADE_DISPATCH_BLOCKED_BY_RUNTIME')
                    if len(paper_trade_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                        paper_trade_examples.append(
                            {
                                'execution_candidate_id': int(candidate.id),
                                'market_id': market_id,
                                'candidate_status': str(candidate.intake_status or ''),
                                'expected_route': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                                'reason_code': 'PAPER_TRADE_BLOCKED_BY_RUNTIME',
                                'blocking_stage': 'dispatch_record',
                                'observed_value': 'missing_dispatch_record',
                                'threshold': 'AutonomousDispatchRecord',
                            }
                        )
                    paper_trade_decision_reason_codes.append('PAPER_TRADE_DECISION_ROUTE_AVAILABLE')
                    continue
                dispatch_status = str(dispatch.dispatch_status or '')
                paper_trade_dispatch_reason_codes.append('PAPER_TRADE_DISPATCH_ROUTE_AVAILABLE')
                final_trade = final_trade_map.get(candidate_id)
                if final_trade is not None or dispatch.linked_paper_trade_id:
                    if dispatch.created_at >= window_start:
                        paper_trade_route_created += 1
                        reason_code = 'PAPER_TRADE_CREATED'
                    else:
                        paper_trade_route_reused += 1
                        reason_code = 'PAPER_TRADE_DEDUPE_REUSED'
                    paper_trade_route_reason_codes.append(reason_code)
                    if len(paper_trade_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                        paper_trade_examples.append(
                            {
                                'execution_candidate_id': int(candidate.id),
                                'market_id': market_id,
                                'candidate_status': str(candidate.intake_status or ''),
                                'expected_route': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                                'reason_code': reason_code,
                                'blocking_stage': 'paper_trade_dispatch',
                                'observed_value': dispatch_status,
                                'threshold': 'FILLED|PARTIAL|DISPATCHED',
                            }
                        )
                    continue
                paper_trade_route_blocked += 1
                if dispatch_status == 'BLOCKED':
                    if decision.decision_type == AutonomousExecutionDecisionType.BLOCK:
                        reason_code = 'PAPER_TRADE_BLOCKED_BY_POLICY'
                    elif decision.decision_type == AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW:
                        reason_code = 'PAPER_TRADE_BLOCKED_BY_SAFETY'
                    else:
                        reason_code = 'PAPER_TRADE_BLOCKED_BY_RUNTIME'
                elif dispatch_status == 'SKIPPED':
                    reason_code = 'PAPER_TRADE_STATUS_FILTER_REJECTED'
                else:
                    reason_code = 'PAPER_TRADE_ARTIFACT_MISMATCH'
                paper_trade_route_reason_codes.append(reason_code)
                final_trade_reason_codes.append('PAPER_TRADE_FINAL_ARTIFACT_MISMATCH_BLOCKED')
                if len(paper_trade_examples) < _PAPER_TRADE_EXAMPLES_LIMIT:
                    paper_trade_examples.append(
                        {
                            'execution_candidate_id': int(candidate.id),
                            'market_id': market_id,
                            'candidate_status': str(candidate.intake_status or ''),
                            'expected_route': _RISK_PAPER_EXECUTION_ROUTE_NAME,
                            'reason_code': reason_code,
                            'blocking_stage': 'paper_trade_dispatch',
                            'observed_value': dispatch_status,
                            'threshold': 'linked_paper_trade_id',
                        }
                    )

    visible_market_ids = [
        _safe_int(getattr(candidate, 'linked_market_id', None))
        for candidate in visible_candidates
        if _safe_int(getattr(candidate, 'linked_market_id', None)) is not None
    ]
    unique_visible_market_count = len(set(visible_market_ids))
    fanout_reason_codes: list[str] = []
    if risk_count := len(risk_rows):
        if risk_count > max(1, len(set(int(getattr(row.linked_candidate, 'id', 0) or 0) for row in risk_rows))):
            fanout_reason_codes.append('LINEAGE_MULTI_RISK_DECISIONS_PER_PREDICTION')
    if paper_trade_route_reused > 0:
        fanout_reason_codes.append('LINEAGE_REUSE_VISIBLE')
    if execution_lineage_deduplicated > 0:
        fanout_reason_codes.append('LINEAGE_DEDUPE_APPLIED')
    if promotion_suppressed_by_active_position > 0:
        fanout_reason_codes.append('EXECUTION_PROMOTION_SUPPRESSED_BY_ACTIVE_POSITION')
    if promotion_suppressed_by_existing_open_trade > 0:
        fanout_reason_codes.append('EXECUTION_PROMOTION_SUPPRESSED_BY_EXISTING_OPEN_TRADE')
    if paper_trade_dispatch_dedupe_applied > 0:
        fanout_reason_codes.append('LINEAGE_DEDUPE_REUSED_EXISTING_DISPATCH')
    if dispatches_deduplicated > 0:
        fanout_reason_codes.append('LINEAGE_DEDUPE_REUSED_EXISTING_TRADE')
    if paper_trade_route_expected > 0 and unique_visible_market_count > 0:
        fanout_ratio = Decimal(str(paper_trade_route_expected)) / Decimal(str(unique_visible_market_count))
        if fanout_ratio > Decimal('3.0'):
            fanout_reason_codes.append('LINEAGE_FANOUT_EXCESSIVE')
        elif fanout_ratio > Decimal('1.0'):
            fanout_reason_codes.append('LINEAGE_FANOUT_EXPECTED')
        else:
            fanout_reason_codes.append('LINEAGE_FANOUT_ONE_TO_ONE')
    else:
        fanout_reason_codes.append('LINEAGE_FANOUT_INSUFFICIENT_DATA')
    normalized_paper_trade_route_codes = list(dict.fromkeys(paper_trade_route_reason_codes))
    normalized_paper_trade_decision_codes = list(dict.fromkeys(paper_trade_decision_reason_codes))
    normalized_paper_trade_dispatch_codes = list(dict.fromkeys(paper_trade_dispatch_reason_codes))
    normalized_final_trade_codes = list(dict.fromkeys(final_trade_reason_codes))
    normalized_runtime_rejection_codes = list(dict.fromkeys(runtime_rejection_reason_codes))
    normalized_fanout_codes = list(dict.fromkeys(fanout_reason_codes))
    normalized_promotion_gate_codes = list(dict.fromkeys(promotion_gate_reason_codes))
    aligned_decision_created = int(paper_trade_decision_created)
    aligned_decision_reused = int(paper_trade_decision_reused)
    promotion_suppressed_total = int(promotion_suppressed_by_active_position + promotion_suppressed_by_existing_open_trade)
    promoted_to_decision = int(len(executable_candidates))
    execution_promotion_gate_summary = {
        'candidates_visible': int(paper_trade_route_expected),
        'candidates_promoted_to_decision': promoted_to_decision,
        'candidates_suppressed_total': promotion_suppressed_total,
        'candidates_suppressed_by_active_position': int(promotion_suppressed_by_active_position),
        'candidates_suppressed_by_existing_open_trade': int(promotion_suppressed_by_existing_open_trade),
        'candidates_allowed_for_exit': int(promotion_allowed_for_exit),
        'candidates_allowed_without_exposure': int(promotion_allowed_without_exposure),
        # Backward-compatible aliases used by existing tests/readers.
        'suppressed_by_active_position': int(promotion_suppressed_by_active_position),
        'suppressed_by_existing_open_trade': int(promotion_suppressed_by_existing_open_trade),
        'allowed_for_exit': int(promotion_allowed_for_exit),
        'allowed_without_exposure': int(promotion_allowed_without_exposure),
        'execution_promotion_gate_reason_codes': normalized_promotion_gate_codes,
    }
    final_fanout_summary = _build_final_fanout_diagnostics(
        executable_candidates=executable_candidates,
        dispatch_by_candidate_id=latest_dispatch_by_candidate,
        final_trade_by_candidate_id=final_trade_map,
        trades_materialized=int(final_trade_created),
        trades_reused=int(final_trade_reused),
        blocked_by_active_position=int(final_trade_blocked_by_active_position),
    )
    cash_pressure_summary = _build_cash_pressure_diagnostics(
        executable_candidates=executable_candidates,
        dispatch_by_candidate_id=latest_dispatch_by_candidate,
        final_trade_reason_codes=normalized_final_trade_codes,
        final_fanout_summary=final_fanout_summary,
        final_trade_created=int(final_trade_created),
        final_trade_reused=int(final_trade_reused),
        final_trade_bridge=final_trade_bridge if executable_candidate_ids else {},
    )
    dominant_blocking_gate = 'NONE'
    if final_trade_blocked_by_active_position > 0:
        dominant_blocking_gate = 'POSITION_EXPOSURE_GATE'
    elif final_trade_blocked_by_cash_precheck > 0:
        dominant_blocking_gate = 'CASH_PRECHECK'
    elif final_trade_blocked > 0:
        dominant_blocking_gate = 'RUNTIME_OR_POLICY'
    secondary_pressure = 'NONE'
    if int(cash_pressure_summary.get('candidates_at_risk_by_cash') or 0) > 0:
        secondary_pressure = 'CASH_PRESSURE_POTENTIAL'
    cash_pressure_summary['dominant_blocking_gate'] = dominant_blocking_gate
    cash_pressure_summary['secondary_pressure'] = secondary_pressure
    position_exposure_summary = _build_position_exposure_summary_from_final_trade_gate(
        final_trade_bridge=final_trade_bridge,
        portfolio_summary=dict(final_trade_bridge.get('portfolio_exposure_context') or {}),
        dominant_blocking_gate=dominant_blocking_gate,
    )
    open_positions_detected = int(position_exposure_summary.get('open_positions_detected') or 0)
    final_trade_blocked_by_active_position = int(position_exposure_summary.get('candidates_blocked_by_active_position') or 0)
    final_trade_allowed_for_exit = int(position_exposure_summary.get('candidates_allowed_for_exit') or 0)
    final_trade_allowed_without_exposure = int(position_exposure_summary.get('candidates_allowed_without_exposure') or 0)
    position_exposure_reason_codes = list(position_exposure_summary.get('position_exposure_reason_codes') or [])
    execution_lineage_summary = {
        'visible_execution_candidates': int(paper_trade_route_expected),
        'executable_candidates': int(len(executable_candidate_ids)),
        'promoted_to_decision': promoted_to_decision,
        'promotion_suppressed_total': promotion_suppressed_total,
        'promotion_suppressed_by_active_position': int(promotion_suppressed_by_active_position),
        'promotion_suppressed_by_existing_open_trade': int(promotion_suppressed_by_existing_open_trade),
        'candidates_considered': int(execution_lineage_considered or len(executable_candidates)),
        'candidates_deduplicated': int(execution_lineage_deduplicated),
        'decisions_created': aligned_decision_created,
        'decisions_reused': aligned_decision_reused,
        'decision_summary_aligned': True,
        'materialized_paper_trades': int(paper_trade_route_created),
        'reused_trade_cycles': int(paper_trade_route_reused),
        'dispatches_considered': int(dispatches_considered),
        'dispatches_deduplicated': int(dispatches_deduplicated),
        'trades_materialized': int(final_trade_created),
        'trades_reused': int(final_trade_reused),
        'final_lineage_count': int(final_fanout_summary.get('final_lineage_count') or 0),
        'unique_market_lineages': int(final_fanout_summary.get('unique_market_lineages') or 0),
        'duplicate_execution_candidates': int(final_fanout_summary.get('duplicate_execution_candidates') or 0),
        'duplicate_dispatches': int(final_fanout_summary.get('duplicate_dispatches') or 0),
        'duplicate_trades': int(final_fanout_summary.get('duplicate_trades') or 0),
        'final_fanout_status': str(final_fanout_summary.get('final_fanout_status') or 'UNKNOWN'),
        'final_fanout_reason_codes': list(final_fanout_summary.get('final_fanout_reason_codes') or []),
        'fanout_reason_codes': normalized_fanout_codes,
        'runtime_rejection_count': int(runtime_rejection_count),
        'runtime_rejection_reason_codes': normalized_runtime_rejection_codes,
        'selected_for_execution': int(final_trade_selected_for_execution),
        'blocked_by_cash_precheck': int(final_trade_blocked_by_cash_precheck),
        'deferred_by_budget': int(final_trade_deferred_by_budget),
        'blocked_by_active_position': int(final_trade_blocked_by_active_position),
        'allowed_for_exit': int(final_trade_allowed_for_exit),
        'allowed_without_exposure': int(final_trade_allowed_without_exposure),
        'open_positions_detected': int(open_positions_detected),
        'position_exposure_reason_codes': list(dict.fromkeys(position_exposure_reason_codes)),
        'cash_throttle_reason_codes': list(dict.fromkeys(final_trade_cash_throttle_reason_codes)),
        'dominant_blocking_gate': dominant_blocking_gate,
        'secondary_pressure': secondary_pressure,
        'execution_promotion_gate_summary': execution_promotion_gate_summary,
    }
    return {
        'paper_execution_route_expected': int(route_expected),
        'paper_execution_route_available': int(route_available),
        'paper_execution_route_attempted': int(route_attempted),
        'paper_execution_route_created': int(route_created),
        'paper_execution_route_reused': int(route_reused),
        'paper_execution_route_blocked': int(route_blocked),
        'paper_execution_route_missing_status_count': int(route_missing_status_count),
        'paper_execution_route_reason_codes': normalized_codes,
        'paper_execution_summary': (
            f"route_expected={route_expected} route_available={route_available} route_attempted={route_attempted} "
            f"route_created={route_created} route_reused={route_reused} route_blocked={route_blocked} "
            f"route_missing_status_count={route_missing_status_count} "
            f"paper_execution_route_reason_codes={','.join(normalized_codes) or 'none'} "
            f"candidates_visible={paper_trade_route_expected} "
            f"promoted_to_decision={promoted_to_decision} "
            f"promotion_suppressed={promotion_suppressed_total} "
            f"promotion_allowed_for_exit={promotion_allowed_for_exit} "
            f"promotion_allowed_without_exposure={promotion_allowed_without_exposure}"
        ),
        'paper_execution_examples': examples,
        'paper_execution_created_count': int(visibility_created_count),
        'paper_execution_reused_count': int(visibility_reused_count),
        'paper_execution_visible_count': int(visibility_visible_count),
        'paper_execution_hidden_count': int(visibility_hidden_count),
        'paper_execution_visibility_reason_codes': normalized_visibility_codes,
        'paper_execution_visibility_summary': (
            f"created={visibility_created_count} reused={visibility_reused_count} "
            f"visible={visibility_visible_count} hidden={visibility_hidden_count} "
            f"paper_execution_visibility_reason_codes={','.join(normalized_visibility_codes) or 'none'} "
            "route_created means AutonomousExecutionReadiness persisted; "
            "funnel visibility uses AutonomousExecutionIntakeCandidate in current window."
        ),
        'paper_execution_visibility_examples': visibility_examples,
        'execution_readiness_available_count': int(len(latest_readiness_by_decision_id)),
        'execution_readiness_created_count': int(execution_readiness_created),
        'execution_readiness_reused_count': int(execution_readiness_reused),
        'execution_candidate_visible_count': int(visibility_visible_count),
        'execution_candidate_created_count': int(execution_candidate_created),
        'execution_candidate_reused_count': int(execution_candidate_reused),
        'execution_candidate_hidden_count': int(visibility_hidden_count),
        'execution_artifact_blocked_count': int(execution_artifact_blocked_count),
        'execution_artifact_reason_codes': normalized_visibility_codes,
        'execution_artifact_summary': (
            f"readiness_available={len(latest_readiness_by_decision_id)} "
            f"readiness_created={execution_readiness_created} readiness_reused={execution_readiness_reused} "
            f"candidate_created={execution_candidate_created} candidate_reused={execution_candidate_reused} "
            f"candidate_visible={visibility_visible_count} candidate_hidden={visibility_hidden_count} "
            f"execution_artifact_blocked_count={execution_artifact_blocked_count} "
            f"execution_artifact_reason_codes={','.join(normalized_visibility_codes) or 'none'}"
        ),
        'execution_artifact_examples': execution_examples,
        'paper_execution_route_bridge_materialized': int(bridge_materialized_count),
        'paper_trade_route_expected': int(paper_trade_route_expected),
        'paper_trade_route_available': int(paper_trade_route_available),
        'paper_trade_route_attempted': int(paper_trade_route_attempted),
        'paper_trade_route_created': int(paper_trade_route_created),
        'paper_trade_route_reused': int(paper_trade_route_reused),
        'paper_trade_route_blocked': int(paper_trade_route_blocked),
        'paper_trade_route_reason_codes': normalized_paper_trade_route_codes,
        'paper_trade_decision_created': aligned_decision_created,
        'paper_trade_decision_reused': aligned_decision_reused,
        'paper_trade_decision_blocked': int(paper_trade_decision_blocked),
        'paper_trade_decision_dedupe_applied': int(paper_trade_decision_dedupe_applied),
        'paper_trade_decision_reason_codes': normalized_paper_trade_decision_codes,
        'paper_trade_dispatch_created': int(paper_trade_dispatch_created),
        'paper_trade_dispatch_reused': int(paper_trade_dispatch_reused),
        'paper_trade_dispatch_blocked': int(paper_trade_dispatch_blocked),
        'paper_trade_dispatch_dedupe_applied': int(paper_trade_dispatch_dedupe_applied),
        'paper_trade_dispatch_reason_codes': normalized_paper_trade_dispatch_codes,
        'paper_trade_dispatch_summary': (
            f"route_expected={paper_trade_route_expected} dispatch_created={paper_trade_dispatch_created} "
            f"dispatch_reused={paper_trade_dispatch_reused} dispatch_blocked={paper_trade_dispatch_blocked} "
            f"dispatch_dedupe_applied={paper_trade_dispatch_dedupe_applied} "
            f"paper_trade_dispatch_reason_codes={','.join(normalized_paper_trade_dispatch_codes) or 'none'}"
        ),
        'paper_trade_dispatch_examples': paper_trade_dispatch_examples[:_PAPER_TRADE_EXAMPLES_LIMIT],
        'final_trade_expected': int(final_trade_expected),
        'final_trade_available': int(final_trade_available),
        'final_trade_attempted': int(final_trade_attempted),
        'final_trade_created': int(final_trade_created),
        'final_trade_reused': int(final_trade_reused),
        'final_trade_blocked': int(final_trade_blocked),
        'cash_available': float(final_trade_cash_available.quantize(Decimal('0.01'))),
        'selected_for_execution': int(final_trade_selected_for_execution),
        'blocked_by_cash_precheck': int(final_trade_blocked_by_cash_precheck),
        'deferred_by_budget': int(final_trade_deferred_by_budget),
        'blocked_by_active_position': int(final_trade_blocked_by_active_position),
        'allowed_for_exit': int(final_trade_allowed_for_exit),
        'allowed_without_exposure': int(final_trade_allowed_without_exposure),
        'open_positions_detected': int(open_positions_detected),
        'position_exposure_reason_codes': list(dict.fromkeys(position_exposure_reason_codes)),
        'cash_budget_remaining': float(final_trade_cash_budget_remaining.quantize(Decimal('0.01'))),
        'cash_throttle_reason_codes': list(dict.fromkeys(final_trade_cash_throttle_reason_codes)),
        'dominant_blocking_gate': dominant_blocking_gate,
        'secondary_pressure': secondary_pressure,
        'final_trade_reason_codes': normalized_final_trade_codes,
        'runtime_rejection_summary': (
            f"runtime_rejection_count={runtime_rejection_count} "
            f"runtime_rejection_reason_codes={','.join(normalized_runtime_rejection_codes) or 'none'}"
        ),
        'runtime_rejection_reason_codes': normalized_runtime_rejection_codes,
        'paper_trade_final_summary': (
            f"expected={final_trade_expected} available={final_trade_available} "
            f"attempted={final_trade_attempted} created={final_trade_created} "
            f"reused={final_trade_reused} blocked={final_trade_blocked} "
            f"cash_available={final_trade_cash_available.quantize(Decimal('0.01'))} "
            f"selected_for_execution={final_trade_selected_for_execution} "
            f"blocked_by_cash_precheck={final_trade_blocked_by_cash_precheck} "
            f"deferred_by_budget={final_trade_deferred_by_budget} "
            f"blocked_by_active_position={final_trade_blocked_by_active_position} "
            f"allowed_for_exit={final_trade_allowed_for_exit} "
            f"allowed_without_exposure={final_trade_allowed_without_exposure} "
            f"open_positions_detected={open_positions_detected} "
            f"cash_budget_remaining={final_trade_cash_budget_remaining.quantize(Decimal('0.01'))} "
            f"dominant_blocking_gate={dominant_blocking_gate} "
            f"secondary_pressure={secondary_pressure} "
            f"position_exposure_reason_codes={','.join(list(dict.fromkeys(position_exposure_reason_codes))) or 'none'} "
            f"cash_throttle_reason_codes={','.join(list(dict.fromkeys(final_trade_cash_throttle_reason_codes))) or 'none'} "
            f"runtime_rejection_count={runtime_rejection_count} "
            f"runtime_rejection_reason_codes={','.join(normalized_runtime_rejection_codes) or 'none'} "
            f"final_trade_reason_codes={','.join(normalized_final_trade_codes) or 'none'}"
        ),
        'paper_trade_final_examples': final_trade_examples[:_PAPER_TRADE_EXAMPLES_LIMIT],
        'final_fanout_summary': final_fanout_summary,
        'final_fanout_examples': list(final_fanout_summary.get('final_fanout_examples') or []),
        'cash_pressure_summary': cash_pressure_summary,
        'cash_pressure_examples': list(cash_pressure_summary.get('cash_pressure_examples') or []),
        'position_exposure_summary': position_exposure_summary,
        'paper_trade_decision_summary': (
            f"route_expected={paper_trade_route_expected} decision_created={paper_trade_decision_created} "
            f"decision_reused={paper_trade_decision_reused} decision_blocked={paper_trade_decision_blocked} "
            f"decision_dedupe_applied={paper_trade_decision_dedupe_applied} "
            f"paper_trade_decision_reason_codes={','.join(normalized_paper_trade_decision_codes) or 'none'} "
            f"promoted_to_decision={promoted_to_decision} "
            f"promotion_suppressed={promotion_suppressed_total}"
        ),
        'paper_trade_decision_examples': paper_trade_decision_examples[:_PAPER_TRADE_EXAMPLES_LIMIT],
        'paper_trade_summary': (
            f"route_expected={paper_trade_route_expected} route_available={paper_trade_route_available} "
            f"route_attempted={paper_trade_route_attempted} route_created={paper_trade_route_created} "
            f"route_reused={paper_trade_route_reused} route_blocked={paper_trade_route_blocked} "
            f"runtime_rejection_count={runtime_rejection_count} "
            f"runtime_rejection_reason_codes={','.join(normalized_runtime_rejection_codes) or 'none'} "
            f"paper_trade_route_reason_codes={','.join(normalized_paper_trade_route_codes) or 'none'} "
            f"execution_promotion_gate_reason_codes={','.join(normalized_promotion_gate_codes) or 'none'}"
        ),
        'paper_trade_examples': paper_trade_examples[:_PAPER_TRADE_EXAMPLES_LIMIT],
        'execution_promotion_gate_summary': execution_promotion_gate_summary,
        'execution_promotion_gate_examples': promotion_gate_examples[:_PAPER_TRADE_EXAMPLES_LIMIT],
        'execution_lineage_summary': execution_lineage_summary,
    }


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _missing_prediction_intake_fields(*, handoff: PredictionHandoffCandidate) -> list[str]:
    missing: list[str] = []
    if getattr(handoff, 'linked_market_id', None) is None:
        missing.append('linked_market_id')
    if getattr(handoff, 'handoff_confidence', None) is None:
        missing.append('handoff_confidence')
    if not str(getattr(handoff, 'handoff_status', '') or '').strip():
        missing.append('handoff_status')
    return missing


def _as_decimal(value: Any, default: str = '0') -> Decimal:
    try:
        return Decimal(str(value if value is not None else default))
    except Exception:
        return Decimal(default)


def _derive_prediction_status_reason(*, candidate: PredictionIntakeCandidate, linked_review: PredictionConvictionReview | None, source: str) -> dict[str, Any]:
    diagnostics = dict((candidate.metadata or {}).get('prediction_intake_status_diagnostics') or {})
    runtime_ready_threshold = diagnostics.get('runtime_ready_confidence_threshold') or str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD)
    monitor_reason = 'PREDICTION_STATUS_NOT_RUNTIME_READY'
    observed_value: Any = str(candidate.intake_status or '')
    threshold: Any = runtime_ready_threshold

    if source == 'reused' and candidate.intake_status == PredictionIntakeStatus.MONITOR_ONLY:
        monitor_reason = 'PREDICTION_STATUS_MONITOR_ONLY_REUSED_STATUS'
        observed_value = str(candidate.intake_status or '')
        threshold = 'current_handoff_not_re-evaluated_in_window'
    elif candidate.intake_status == PredictionIntakeStatus.READY_FOR_RUNTIME:
        reason_codes = set(candidate.reason_codes or [])
        monitor_reason = 'PREDICTION_STATUS_READY_WITH_CAUTION' if 'PREDICTION_STATUS_READY_WITH_CAUTION' in reason_codes else 'PREDICTION_STATUS_READY_FOR_RUNTIME'
        observed_value = str(candidate.handoff_confidence)
    elif candidate.intake_status == PredictionIntakeStatus.BLOCKED:
        monitor_reason = 'PREDICTION_STATUS_BLOCKED_BY_RULE'
        observed_value = str(getattr(getattr(candidate, 'linked_market', None), 'current_market_probability', ''))
        threshold = 'market_probability_required'
    elif candidate.intake_status == PredictionIntakeStatus.MONITOR_ONLY:
        confidence = _as_decimal(getattr(candidate, 'handoff_confidence', None))
        narrative = _as_decimal(getattr(candidate, 'narrative_priority', None))
        structural = _as_decimal(getattr(candidate, 'structural_priority', None))
        if confidence < _PREDICTION_INTAKE_CONFIDENCE_THRESHOLD:
            monitor_reason = 'PREDICTION_STATUS_MONITOR_ONLY_LOW_CONFIDENCE'
            observed_value = str(confidence)
            threshold = runtime_ready_threshold
        elif narrative < Decimal('0.6500') or structural < Decimal('0.7000'):
            monitor_reason = 'PREDICTION_STATUS_MONITOR_ONLY_LOW_EDGE'
            observed_value = {'narrative_priority': str(narrative), 'structural_priority': str(structural)}
            threshold = diagnostics.get('runtime_ready_with_caution_threshold') or 'lineage_strength'
        elif linked_review and _as_decimal(getattr(linked_review, 'uncertainty', None)) > Decimal('0.6500'):
            monitor_reason = 'PREDICTION_STATUS_MONITOR_ONLY_HIGH_UNCERTAINTY'
            observed_value = str(linked_review.uncertainty)
            threshold = 'uncertainty<=0.6500'

    return {
        'status_reason_code': monitor_reason,
        'runtime_ready_threshold': runtime_ready_threshold,
        'observed_value': observed_value,
        'threshold': threshold,
        'source_stage': diagnostics.get('handler') or 'prediction_intake',
    }


def _has_policy_risk_safety_signal(*, codes: list[Any]) -> bool:
    tokens = {'POLICY', 'RISK', 'SAFETY', 'BLOCK', 'GUARDRAIL'}
    for code in codes:
        text = str(code or '').upper()
        if any(token in text for token in tokens):
            return True
    return False


def _evaluate_prediction_risk_with_caution(
    *,
    candidate: PredictionIntakeCandidate,
    linked_review: PredictionConvictionReview | None,
    preset_name: str,
) -> dict[str, Any]:
    confidence = _as_decimal(getattr(candidate, 'handoff_confidence', None))
    edge = _as_decimal(getattr(candidate, 'structural_priority', None))
    runtime_ready_threshold = str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD)
    caution_band = f'[{_PREDICTION_RISK_CAUTION_BAND_MIN},{_PREDICTION_RISK_CAUTION_BAND_MAX})'
    decision_source = 'mission_control_prediction_risk_with_caution_v1'
    handoff_status = str((candidate.metadata or {}).get('handoff_status') or '').strip()
    pursuit_bucket = str((candidate.metadata or {}).get('pursuit_priority_bucket') or '').strip()
    has_consensus = bool(candidate.linked_consensus_record_id)
    policy_signal = _has_policy_risk_safety_signal(codes=list(candidate.reason_codes or []))
    if linked_review:
        policy_signal = policy_signal or _has_policy_risk_safety_signal(codes=list(linked_review.reason_codes or []))

    if preset_name != PRESET_NAME:
        return {
            'eligible': False,
            'reason_code': 'PREDICTION_RISK_WITH_CAUTION_NOT_IN_BAND',
            'confidence': confidence,
            'edge': edge,
            'runtime_ready_threshold': runtime_ready_threshold,
            'caution_band': caution_band,
            'decision_source': decision_source,
        }
    if not (_PREDICTION_RISK_CAUTION_BAND_MIN <= confidence < _PREDICTION_RISK_CAUTION_BAND_MAX):
        return {
            'eligible': False,
            'reason_code': 'PREDICTION_RISK_WITH_CAUTION_NOT_IN_BAND',
            'confidence': confidence,
            'edge': edge,
            'runtime_ready_threshold': runtime_ready_threshold,
            'caution_band': caution_band,
            'decision_source': decision_source,
        }
    if edge < _PREDICTION_RISK_CAUTION_MIN_EDGE:
        return {
            'eligible': False,
            'reason_code': 'PREDICTION_RISK_WITH_CAUTION_BLOCKED_BY_LOW_EDGE',
            'confidence': confidence,
            'edge': edge,
            'runtime_ready_threshold': runtime_ready_threshold,
            'caution_band': caution_band,
            'decision_source': decision_source,
        }
    if not handoff_status or not pursuit_bucket or not has_consensus:
        return {
            'eligible': False,
            'reason_code': 'PREDICTION_RISK_WITH_CAUTION_BLOCKED_BY_WEAK_LINEAGE',
            'confidence': confidence,
            'edge': edge,
            'runtime_ready_threshold': runtime_ready_threshold,
            'caution_band': caution_band,
            'decision_source': decision_source,
        }
    if candidate.linked_market_id is None or policy_signal:
        return {
            'eligible': False,
            'reason_code': 'PREDICTION_RISK_WITH_CAUTION_BLOCKED_BY_POLICY_SIGNAL',
            'confidence': confidence,
            'edge': edge,
            'runtime_ready_threshold': runtime_ready_threshold,
            'caution_band': caution_band,
            'decision_source': decision_source,
        }
    return {
        'eligible': True,
        'reason_code': 'PREDICTION_RISK_WITH_CAUTION_ELIGIBLE',
        'confidence': confidence,
        'edge': edge,
        'runtime_ready_threshold': runtime_ready_threshold,
        'caution_band': caution_band,
        'decision_source': decision_source,
    }


def _materialize_prediction_artifacts_for_risk(
    *,
    candidates: list[PredictionIntakeCandidate],
    conviction_by_candidate_id: dict[int, PredictionConvictionReview],
) -> tuple[dict[str, Any], dict[int, PredictionConvictionReview], dict[int, RiskReadyPredictionHandoff], set[int]]:
    review_ids = [review.id for review in conviction_by_candidate_id.values()]
    handoff_by_review_id: dict[int, RiskReadyPredictionHandoff] = {}
    if review_ids:
        for handoff in (
            RiskReadyPredictionHandoff.objects.filter(linked_conviction_review_id__in=review_ids).order_by('linked_conviction_review_id', '-created_at', '-id')
        ):
            review_id = int(handoff.linked_conviction_review_id)
            if review_id not in handoff_by_review_id:
                handoff_by_review_id[review_id] = handoff

    summary: dict[str, Any] = {
        'prediction_artifact_expected_count': 0,
        'conviction_review_available_count': 0,
        'conviction_review_created_count': 0,
        'conviction_review_reused_count': 0,
        'risk_ready_handoff_available_count': 0,
        'risk_ready_handoff_created_count': 0,
        'risk_ready_handoff_reused_count': 0,
        'prediction_artifact_blocked_count': 0,
        'prediction_artifact_reason_codes': [],
        'prediction_artifact_examples': [],
    }
    route_resolved_candidate_ids: set[int] = set()
    handoff_by_candidate_id: dict[int, RiskReadyPredictionHandoff] = {}
    reason_codes: list[str] = []

    for candidate in candidates:
        summary['prediction_artifact_expected_count'] += 1
        candidate_id = int(candidate.id)
        review = conviction_by_candidate_id.get(candidate_id)
        if review is None:
            reason_codes.append('PREDICTION_CONVICTION_REVIEW_MISSING')
            review = review_candidate(intake_candidate=candidate)
            conviction_by_candidate_id[candidate_id] = review
            summary['conviction_review_created_count'] += 1
            reason_codes.append('PREDICTION_CONVICTION_REVIEW_CREATED')
            created_artifact = 'PredictionConvictionReview'
            reused_artifact = None
        else:
            summary['conviction_review_reused_count'] += 1
            reason_codes.append('PREDICTION_CONVICTION_REVIEW_REUSED')
            created_artifact = None
            reused_artifact = 'PredictionConvictionReview'
        summary['conviction_review_available_count'] += 1

        handoff = handoff_by_review_id.get(int(review.id))
        if handoff is None:
            reason_codes.append('PREDICTION_RISK_READY_HANDOFF_MISSING')
            handoff = build_risk_ready_handoff(review=review)
            handoff_by_review_id[int(review.id)] = handoff
            summary['risk_ready_handoff_created_count'] += 1
            reason_codes.append('PREDICTION_RISK_READY_HANDOFF_CREATED')
            created_artifact = 'RiskReadyPredictionHandoff'
        else:
            summary['risk_ready_handoff_reused_count'] += 1
            reason_codes.append('PREDICTION_RISK_READY_HANDOFF_REUSED')
            reused_artifact = 'RiskReadyPredictionHandoff'
        summary['risk_ready_handoff_available_count'] += 1
        handoff_by_candidate_id[candidate_id] = handoff
        route_resolved_candidate_ids.add(candidate_id)
        reason_codes.append('PREDICTION_ARTIFACT_MISMATCH_RESOLVED')
        if len(summary['prediction_artifact_examples']) < 3:
            summary['prediction_artifact_examples'].append(
                {
                    'candidate_id': candidate_id,
                    'market_id': _safe_int(candidate.linked_market_id),
                    'source_model': 'PredictionIntakeCandidate',
                    'expected_artifact': 'RiskReadyPredictionHandoff',
                    'created_artifact': created_artifact,
                    'reused_artifact': reused_artifact,
                    'reason_code': 'PREDICTION_ARTIFACT_MISMATCH_RESOLVED',
                    'blocking_stage': '',
                }
            )

    summary['prediction_artifact_reason_codes'] = list(dict.fromkeys(reason_codes))
    summary['prediction_artifact_summary'] = (
        f"artifact_expected={summary['prediction_artifact_expected_count']} "
        f"conviction_review_available={summary['conviction_review_available_count']} "
        f"conviction_review_created={summary['conviction_review_created_count']} "
        f"conviction_review_reused={summary['conviction_review_reused_count']} "
        f"risk_ready_handoff_available={summary['risk_ready_handoff_available_count']} "
        f"risk_ready_handoff_created={summary['risk_ready_handoff_created_count']} "
        f"risk_ready_handoff_reused={summary['risk_ready_handoff_reused_count']} "
        f"artifact_blocked={summary['prediction_artifact_blocked_count']} "
        f"prediction_artifact_reason_codes={','.join(summary['prediction_artifact_reason_codes']) or 'none'}"
    )
    return summary, conviction_by_candidate_id, handoff_by_candidate_id, route_resolved_candidate_ids


def _evaluate_borderline_handoff(*, handoff: PredictionHandoffCandidate, preset_name: str) -> dict[str, Any]:
    confidence = _as_decimal(getattr(handoff, 'handoff_confidence', None))
    in_band = _BORDERLINE_CONFIDENCE_MIN <= confidence < _BORDERLINE_CONFIDENCE_MAX
    if not in_band:
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_NOT_IN_BAND',
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    if preset_name != PRESET_NAME:
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_OUT_OF_SCOPE',
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    if getattr(handoff, 'handoff_status', None) != PredictionHandoffStatus.DEFERRED:
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_BY_STATUS',
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    missing_fields = _missing_prediction_intake_fields(handoff=handoff)
    if missing_fields:
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_BY_COMPONENTS',
            'missing_fields': missing_fields,
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    market_probability = getattr(getattr(handoff, 'linked_market', None), 'current_market_probability', None)
    if market_probability is None or getattr(handoff, 'linked_market_id', None) is None:
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_BY_COMPONENTS',
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    if list(getattr(handoff, 'handoff_reason_codes', []) or []):
        blocked_codes = {'BLOCKED', 'RULE', 'POLICY', 'SAFETY'}
        if any(any(token in str(code).upper() for token in blocked_codes) for code in handoff.handoff_reason_codes):
            return {
                'eligible': False,
                'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_BY_COMPONENTS',
                'confidence': confidence,
                'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
                'decision_source': _BORDERLINE_DECISION_SOURCE,
            }
    structural_diagnostics = _evaluate_structural_guardrail(handoff=handoff, preset_name=preset_name)
    if structural_diagnostics.get('blocked'):
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_BY_STRUCTURAL_WEAKNESS',
            'structural_reason_code': structural_diagnostics.get('structural_reason_code'),
            'structural_status': structural_diagnostics.get('structural_status'),
            'weak_components': structural_diagnostics.get('weak_components'),
            'strong_components': structural_diagnostics.get('strong_components'),
            'observed_values': structural_diagnostics.get('observed_values'),
            'thresholds': structural_diagnostics.get('thresholds'),
            'structural_rule_type': structural_diagnostics.get('structural_rule_type'),
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    score_components = dict(getattr(getattr(handoff, 'linked_pursuit_score', None), 'score_components', {}) or {})
    narrative_priority = _as_decimal(score_components.get('narrative_priority'))
    divergence_strength = _as_decimal(score_components.get('divergence_strength'))
    if narrative_priority < _BORDERLINE_MIN_NARRATIVE_PRIORITY:
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_BY_LOW_NARRATIVE_PRIORITY',
            'observed_value': str(narrative_priority.quantize(Decimal('0.0001'))),
            'threshold': str(_BORDERLINE_MIN_NARRATIVE_PRIORITY),
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    if divergence_strength < _BORDERLINE_MIN_DIVERGENCE_STRENGTH:
        return {
            'eligible': False,
            'reason_code': 'HANDOFF_BORDERLINE_BLOCKED_BY_LOW_DIVERGENCE',
            'observed_value': str(divergence_strength.quantize(Decimal('0.0001'))),
            'threshold': str(_BORDERLINE_MIN_DIVERGENCE_STRENGTH),
            'confidence': confidence,
            'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
            'decision_source': _BORDERLINE_DECISION_SOURCE,
        }
    return {
        'eligible': True,
        'reason_code': 'HANDOFF_BORDERLINE_ELIGIBLE',
        'structural_reason_code': structural_diagnostics.get('structural_reason_code'),
        'structural_status': structural_diagnostics.get('structural_status'),
        'weak_components': structural_diagnostics.get('weak_components'),
        'strong_components': structural_diagnostics.get('strong_components'),
        'observed_values': structural_diagnostics.get('observed_values'),
        'thresholds': structural_diagnostics.get('thresholds'),
        'structural_override_enabled': structural_diagnostics.get('override_enabled'),
        'structural_override_applied': structural_diagnostics.get('override_applied'),
        'structural_rule_type': structural_diagnostics.get('structural_rule_type'),
        'confidence': confidence,
        'band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
        'decision_source': _BORDERLINE_DECISION_SOURCE,
    }


def _handoff_status_reason(*, handoff: PredictionHandoffCandidate) -> tuple[str, str, Any, Any, dict[str, Any]]:
    status = str(getattr(handoff, 'handoff_status', '') or '')
    confidence_raw = getattr(handoff, 'handoff_confidence', None)
    confidence = Decimal(str(confidence_raw or '0'))
    score_status = str(getattr(getattr(handoff, 'linked_pursuit_score', None), 'score_status', '') or '')
    structural_status = str(getattr(getattr(handoff, 'linked_assessment', None), 'structural_status', '') or '')
    has_consensus = bool(getattr(handoff, 'linked_consensus_record_id', None))
    score_components = dict(getattr(getattr(handoff, 'linked_pursuit_score', None), 'score_components', {}) or {})
    base_context = {
        'score_status': score_status,
        'structural_status': structural_status,
        'has_consensus_link': has_consensus,
        'score_components': score_components,
    }

    if status == PredictionHandoffStatus.READY:
        if has_consensus:
            return (
                'HANDOFF_STATUS_READY_BY_CONSENSUS',
                'consensus',
                True,
                True,
                base_context,
            )
        return (
            'HANDOFF_STATUS_READY_BY_PURSUIT',
            'pursuit',
            score_status or status,
            'ready_for_prediction',
            base_context,
        )

    if status == PredictionHandoffStatus.BLOCKED:
        return (
            'HANDOFF_STATUS_BLOCKED_BY_RULE',
            'handoff_scoring',
            structural_status or score_status or status,
            'non_blocked_structural_status',
            base_context,
        )

    if status == PredictionHandoffStatus.DEFERRED:
        if confidence < _PREDICTION_INTAKE_CONFIDENCE_THRESHOLD:
            return (
                'HANDOFF_STATUS_DEFERRED_LOW_CONFIDENCE',
                'handoff_scoring',
                str(confidence.quantize(Decimal('0.0001'))),
                str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD),
                base_context,
            )
        if structural_status == 'deferred':
            return (
                'HANDOFF_STATUS_DEFERRED_INSUFFICIENT_EVIDENCE',
                'pursuit',
                structural_status,
                'prediction_ready',
                base_context,
            )
        return (
            'HANDOFF_STATUS_DEFERRED_NO_PROMOTION',
            'pursuit',
            score_status or structural_status or status,
            'ready_for_prediction',
            base_context,
        )

    return (
        'HANDOFF_STATUS_DEFERRED_NO_PROMOTION',
        'handoff_scoring',
        status,
        PredictionHandoffStatus.READY,
        base_context,
    )


@dataclass(frozen=True)
class FunnelCounts:
    scan_count: int
    research_count: int
    prediction_count: int
    risk_approved_count: int
    risk_blocked_count: int
    paper_execution_count: int
    recent_trades_count: int


def _count_recent_trades_from_summary(*, window_start) -> int:
    account = get_active_account()
    summary = build_account_summary(account=account)
    recent_trades = summary.get('recent_trades') or []
    total = 0
    for trade in recent_trades:
        executed_at = trade.get('executed_at')
        if executed_at and executed_at >= window_start:
            total += 1
    return total


def _collect_funnel_counts(*, window_start) -> FunnelCounts:
    scan_count = MarketUniverseScanRun.objects.filter(started_at__gte=window_start).aggregate(
        total=Sum('markets_considered')
    ).get('total') or 0
    research_count = PredictionHandoffCandidate.objects.filter(created_at__gte=window_start).count()
    prediction_count = PredictionConvictionReview.objects.filter(created_at__gte=window_start).count()
    risk_approved_count = RiskApprovalDecision.objects.filter(
        created_at__gte=window_start,
        approval_status__in=['APPROVED', 'APPROVED_REDUCED'],
    ).count()
    risk_blocked_count = RiskApprovalDecision.objects.filter(
        created_at__gte=window_start,
        approval_status='BLOCKED',
    ).count()
    paper_execution_count = AutonomousTradeCycleRun.objects.filter(started_at__gte=window_start).aggregate(
        total=Sum('executed_paper_trade_count')
    ).get('total') or 0

    recent_trade_count = _count_recent_trades_from_summary(window_start=window_start)
    if recent_trade_count == 0:
        recent_trade_count = PaperTrade.objects.filter(
            status=PaperTradeStatus.EXECUTED,
            executed_at__gte=window_start,
        ).count()

    return FunnelCounts(
        scan_count=int(scan_count),
        research_count=int(research_count),
        prediction_count=int(prediction_count),
        risk_approved_count=int(risk_approved_count),
        risk_blocked_count=int(risk_blocked_count),
        paper_execution_count=int(paper_execution_count),
        recent_trades_count=int(recent_trade_count),
    )


def _stage_status(count: int) -> str:
    if count <= 0:
        return STAGE_EMPTY
    if count < _LOW_THRESHOLD:
        return STAGE_LOW
    return STAGE_ACTIVE


def _infer_status(*, counts: FunnelCounts) -> str:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    stages_non_zero = sum(
        1 for value in [counts.scan_count, counts.research_count, counts.prediction_count, risk_total, counts.paper_execution_count] if value > 0
    )
    if stages_non_zero >= 3 and (risk_total > 0 or counts.paper_execution_count > 0):
        return FUNNEL_ACTIVE
    if counts.scan_count == 0 and counts.research_count == 0 and counts.prediction_count == 0 and risk_total == 0 and counts.paper_execution_count == 0:
        return FUNNEL_STALLED
    if counts.scan_count > 0 and counts.research_count == 0 and counts.prediction_count == 0 and risk_total == 0 and counts.paper_execution_count == 0:
        return FUNNEL_STALLED
    return FUNNEL_THIN_FLOW


def _infer_top_stage(*, counts: FunnelCounts) -> str:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    ranked = [
        ('scan', counts.scan_count),
        ('research', counts.research_count),
        ('prediction', counts.prediction_count),
        ('risk', risk_total),
        ('paper_execution', counts.paper_execution_count),
    ]
    return max(ranked, key=lambda row: row[1])[0]


def _infer_stalled_stage(*, counts: FunnelCounts) -> str | None:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    sequence = [
        ('scan', counts.scan_count),
        ('research', counts.research_count),
        ('prediction', counts.prediction_count),
        ('risk', risk_total),
        ('paper_execution', counts.paper_execution_count),
    ]
    for index in range(1, len(sequence)):
        previous = sequence[index - 1][1]
        current = sequence[index][1]
        if previous > 0 and current == 0:
            return sequence[index][0]
    return None


def _infer_hint(*, status: str, counts: FunnelCounts, stalled_stage: str | None) -> str:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    if counts.risk_blocked_count > 0 and counts.risk_blocked_count >= max(counts.risk_approved_count, 1):
        return 'Risk is blocking most candidates'
    if status == FUNNEL_ACTIVE:
        return 'Autonomy funnel appears healthy'
    if counts.scan_count == 0:
        return 'No recent scan activity detected'
    if counts.prediction_count > 0 and risk_total == 0:
        return 'Flow is thin after prediction'
    if stalled_stage:
        return f'Flow is thin after {stalled_stage}'
    return 'Wait for another cycle and refresh'


def _signal_market_link_tokens(*, signal_row: dict[str, Any]) -> list[str]:
    joined = ' '.join([str(signal_row.get('topic') or ''), str(signal_row.get('canonical_label') or '')]).lower()
    normalized = re.sub(r'[^a-z0-9\s]+', ' ', joined)
    return [token for token in normalized.split() if len(token) >= 3 and token not in _TOKEN_STOPWORDS]


def _candidate_market_scores(*, signal_row: dict[str, Any], active_markets: list[dict[str, Any]]) -> list[tuple[Decimal, int]]:
    tokens = _signal_market_link_tokens(signal_row=signal_row)
    if not tokens:
        return []

    scored: list[tuple[Decimal, int]] = []
    for market in active_markets:
        market_id = market.get('id')
        if market_id is None:
            continue
        corpus = ' '.join(
            [
                str(market.get('title') or ''),
                str(market.get('category') or ''),
                str(market.get('ticker') or ''),
                str(market.get('slug') or ''),
            ]
        ).lower()
        token_hits = sum(1 for token in tokens if token in corpus)
        if token_hits == 0:
            continue
        score = Decimal(token_hits)
        if str(market.get('source_type') or '') == 'demo':
            score += Decimal('0.20')
        if str(market.get('status') or '') == 'open':
            score += Decimal('0.20')
        scored.append((score, int(market_id)))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return scored


def _resolve_market_link_for_shortlist_signal(*, signal_row: dict[str, Any], active_markets: list[dict[str, Any]]) -> dict[str, Any]:
    linked_market_id = signal_row.get('linked_market_id')
    if linked_market_id is not None:
        return {
            'attempted': False,
            'resolved': True,
            'ambiguous': False,
            'chosen_market_id': int(linked_market_id),
            'candidate_count': 1,
            'reason_code': 'MARKET_LINK_REUSED_EXISTING_MATCH',
        }

    target_market_id = signal_row.get('target_market_id')
    if target_market_id is not None:
        return {
            'attempted': True,
            'resolved': True,
            'ambiguous': False,
            'chosen_market_id': int(target_market_id),
            'candidate_count': 1,
            'reason_code': 'MARKET_LINK_REUSED_EXISTING_MATCH',
        }

    if not str(signal_row.get('topic') or '').strip() and not str(signal_row.get('canonical_label') or '').strip():
        return {
            'attempted': True,
            'resolved': False,
            'ambiguous': False,
            'chosen_market_id': None,
            'candidate_count': 0,
            'reason_code': 'MARKET_LINK_MISSING_REQUIRED_FIELDS',
        }

    scored_candidates = _candidate_market_scores(signal_row=signal_row, active_markets=active_markets)
    if not scored_candidates:
        return {
            'attempted': True,
            'resolved': False,
            'ambiguous': False,
            'chosen_market_id': None,
            'candidate_count': 0,
            'reason_code': 'MARKET_LINK_NO_CANDIDATES',
        }

    top_score, chosen_market_id = scored_candidates[0]
    second_score = scored_candidates[1][0] if len(scored_candidates) > 1 else Decimal('0')
    if top_score < _MARKET_LINK_CONFIDENCE_THRESHOLD:
        return {
            'attempted': True,
            'resolved': False,
            'ambiguous': False,
            'chosen_market_id': None,
            'candidate_count': len(scored_candidates),
            'reason_code': 'MARKET_LINK_BELOW_CONFIDENCE_THRESHOLD',
        }
    if len(scored_candidates) > 1 and top_score == second_score:
        return {
            'attempted': True,
            'resolved': False,
            'ambiguous': True,
            'chosen_market_id': None,
            'candidate_count': len(scored_candidates),
            'reason_code': 'MARKET_LINK_AMBIGUOUS',
        }

    metadata = signal_row.get('metadata') or {}
    fallback_reason = 'MARKET_LINK_RESOLVED'
    if bool(metadata.get('is_demo')) or bool(metadata.get('demo_shortlist_override')):
        fallback_reason = 'MARKET_LINK_DEMO_FALLBACK_USED'
    return {
        'attempted': True,
        'resolved': True,
        'ambiguous': False,
        'chosen_market_id': int(chosen_market_id),
        'candidate_count': len(scored_candidates),
        'reason_code': fallback_reason,
    }


def _build_handoff_diagnostics(*, window_start, preset_name: str = PRESET_NAME) -> dict[str, Any]:
    prediction_intake_route_disabled = _is_prediction_intake_route_disabled()
    prediction_intake_handler_available = _is_prediction_intake_handler_available()
    shortlisted_qs = NarrativeSignal.objects.filter(
        status=NarrativeSignalStatus.SHORTLISTED,
        created_at__gte=window_start,
    )
    handoff_qs = PredictionHandoffCandidate.objects.filter(created_at__gte=window_start)
    consensus_qs = NarrativeConsensusRecord.objects.filter(created_at__gte=window_start)
    prediction_qs = PredictionConvictionReview.objects.filter(created_at__gte=window_start)
    intake_run_qs = PredictionIntakeRun.objects.filter(created_at__gte=window_start)
    intake_candidate_qs = PredictionIntakeCandidate.objects.filter(created_at__gte=window_start)
    risk_qs = RiskApprovalDecision.objects.filter(created_at__gte=window_start)

    shortlisted_rows = list(
        shortlisted_qs.values('id', 'linked_market_id', 'target_market_id', 'topic', 'canonical_label', 'metadata')[:50]
    )
    shortlisted_count = len(shortlisted_rows)
    handoff_count = handoff_qs.count()
    consensus_count = consensus_qs.count()
    prediction_count = prediction_qs.count()
    intake_run_count = intake_run_qs.count()
    intake_candidate_count = intake_candidate_qs.count()
    risk_count = risk_qs.count()
    risk_rows = list(
        risk_qs.select_related('linked_candidate')
        .order_by('-created_at', '-id')[:40]
    )
    paper_execution_summary = _build_paper_execution_diagnostics(risk_rows=risk_rows, window_start=window_start)
    paper_execution_count = int(paper_execution_summary.get('paper_execution_visible_count') or 0)

    shortlist_market_ids = {
        market_id
        for market_id in [row.get('linked_market_id') for row in shortlisted_rows]
        if market_id is not None
    }
    shortlist_cluster_ids = {
        cluster_id
        for cluster_id in shortlisted_qs.values_list('linked_cluster_id', flat=True)
        if cluster_id is not None
    }
    handoff_market_ids = {
        market_id
        for market_id in handoff_qs.values_list('linked_market_id', flat=True)
        if market_id is not None
    }
    prediction_market_ids = {
        market_id
        for market_id in prediction_qs.values_list('linked_intake_candidate__linked_market_id', flat=True)
        if market_id is not None
    }
    risk_market_ids = {
        market_id
        for market_id in risk_qs.values_list('linked_candidate__linked_market_id', flat=True)
        if market_id is not None
    }

    handoff_reason_codes: list[str] = []
    stage_source_mismatch: dict[str, Any] = {}
    prediction_intake_reason_codes: list[str] = []
    prediction_intake_examples: list[dict[str, Any]] = []
    prediction_visibility_examples: list[dict[str, Any]] = []
    shortlist_handoff_summary = {
        'shortlisted_signals': int(shortlisted_count),
        'shortlisted_signal_ids': [int(row.get('id') or 0) for row in shortlisted_rows[:3]],
        'shortlisted_market_ids': sorted(list(shortlist_market_ids))[:3],
        'handoff_attempted': 0,
        'handoff_created': 0,
        'handoff_blocked': 0,
        'shortlist_handoff_reason_codes': [],
        'shortlist_handoff_examples': [],
        'summary': '',
    }
    active_markets = list(
        Market.objects.filter(is_active=True).values('id', 'title', 'category', 'ticker', 'slug', 'source_type', 'status')[:300]
    )
    market_link_attempted = 0
    market_link_resolved = 0
    market_link_missing = 0
    market_link_ambiguous = 0
    market_link_reason_codes: list[str] = []
    market_link_examples: list[dict[str, Any]] = []
    resolved_market_by_signal_id: dict[int, int] = {}

    route_available = not prediction_intake_route_disabled and prediction_intake_handler_available
    eligible_handoff_rows = list(
        PredictionHandoffCandidate.objects.filter(
            created_at__gte=window_start,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence__gte=Decimal('0.5500'),
            linked_market__current_market_probability__isnull=False,
        ).values_list('id', flat=True)
    )
    eligible_handoff_ids = {int(handoff_id) for handoff_id in eligible_handoff_rows}
    borderline_diagnostics_by_handoff: dict[int, dict[str, Any]] = {}
    bridge_attempted = False
    bridge_created_handoff_ids: set[int] = set()

    for row in shortlisted_rows:
        signal_id = int(row.get('id') or 0)
        outcome = _resolve_market_link_for_shortlist_signal(signal_row=row, active_markets=active_markets)
        if outcome['attempted']:
            market_link_attempted += 1
        if outcome['resolved']:
            market_link_resolved += 1
            chosen_id = outcome.get('chosen_market_id')
            if chosen_id is not None:
                resolved_market_by_signal_id[signal_id] = int(chosen_id)
                shortlist_market_ids.add(int(chosen_id))
        else:
            market_link_missing += 1
        if outcome['ambiguous']:
            market_link_ambiguous += 1
        market_link_reason_codes.append(str(outcome.get('reason_code') or 'MARKET_LINK_FILTERED_OUT'))
        if len(market_link_examples) < 3:
            market_link_examples.append(
                {
                    'signal_id': signal_id,
                    'candidate_count': int(outcome.get('candidate_count') or 0),
                    'chosen_market_id': outcome.get('chosen_market_id'),
                    'reason_code': str(outcome.get('reason_code') or ''),
                }
            )

    normalized_market_link_codes = list(dict.fromkeys(market_link_reason_codes))
    market_link_summary = {
        'shortlisted_signals': int(shortlisted_count),
        'market_link_attempted': int(market_link_attempted),
        'market_link_resolved': int(market_link_resolved),
        'market_link_missing': int(market_link_missing),
        'market_link_ambiguous': int(market_link_ambiguous),
        'market_link_reason_codes': normalized_market_link_codes,
        'market_link_summary': (
            f"shortlisted_signals={shortlisted_count} market_link_attempted={market_link_attempted} "
            f"market_link_resolved={market_link_resolved} market_link_missing={market_link_missing} "
            f"market_link_ambiguous={market_link_ambiguous} "
            f"market_link_reason_codes={','.join(normalized_market_link_codes) or 'none'}"
        ),
    }

    recent_pursuit_run_count = ResearchPursuitRun.objects.filter(started_at__gte=window_start).count()
    assessed_market_ids = {
        market_id
        for market_id in ResearchStructuralAssessment.objects.filter(created_at__gte=window_start).values_list('linked_market_id', flat=True)
        if market_id is not None
    }
    priority_by_market: dict[int, str] = {}
    for market_id, status in ResearchHandoffPriority.objects.filter(
        created_at__gte=window_start,
        linked_market_id__in=list(shortlist_market_ids),
    ).values_list('linked_market_id', 'handoff_status'):
        if market_id is not None and market_id not in priority_by_market:
            priority_by_market[market_id] = status
    previous_handoff_market_ids = {
        market_id
        for market_id in PredictionHandoffCandidate.objects.filter(linked_market_id__in=list(shortlist_market_ids), created_at__lt=window_start).values_list(
            'linked_market_id', flat=True
        )
        if market_id is not None
    }

    shortlist_reason_codes: list[str] = []
    shortlist_examples: list[dict[str, Any]] = []
    attempted_count = 0
    created_count = 0
    blocked_count = 0
    route_expected_count = 0
    route_available_count = 0
    route_missing_count = 0
    route_attempted_count = 0
    route_created_count = 0
    route_blocked_count = 0
    downstream_route_reason_codes: list[str] = []
    downstream_route_examples: list[dict[str, Any]] = []
    route_disabled = _is_downstream_route_disabled()
    route_handler_available = _is_downstream_route_handler_available()

    for row in shortlisted_rows:
        signal_id = int(row.get('id') or 0)
        market_id = row.get('linked_market_id') or resolved_market_by_signal_id.get(signal_id)
        downstream_reason = 'DOWNSTREAM_ROUTE_FILTERED_OUT'
        expected_route = _DOWNSTREAM_ROUTE_NAME if market_id is not None else None
        reason = 'SHORTLIST_BLOCKED_BY_FILTER'
        blocked = True
        attempted = False
        created = False

        if market_id is None:
            reason = 'SHORTLIST_BLOCKED_NO_MARKET_LINK'
            downstream_reason = 'DOWNSTREAM_ROUTE_FILTERED_OUT'
        elif route_disabled:
            reason = 'SHORTLIST_BLOCKED_NO_DOWNSTREAM_ROUTE'
            downstream_reason = 'DOWNSTREAM_ROUTE_DISABLED'
        elif not route_handler_available:
            reason = 'SHORTLIST_BLOCKED_NO_DOWNSTREAM_ROUTE'
            downstream_reason = 'DOWNSTREAM_ROUTE_NO_ELIGIBLE_HANDLER'
        elif market_id in handoff_market_ids:
            reason = 'SHORTLIST_PROMOTED_TO_HANDOFF'
            attempted = True
            created = True
            blocked = False
            downstream_reason = 'DOWNSTREAM_ROUTE_CREATED_HANDOFF'
        elif market_id in assessed_market_ids:
            reason = 'SHORTLIST_BLOCKED_BY_FILTER'
            attempted = True
            downstream_reason = 'DOWNSTREAM_ROUTE_BLOCKED_BY_GUARDRAIL'
        elif recent_pursuit_run_count == 0:
            reason = 'SHORTLIST_BLOCKED_NO_DOWNSTREAM_ROUTE'
            downstream_reason = 'DOWNSTREAM_ROUTE_MISSING'
        elif market_id in previous_handoff_market_ids:
            reason = 'SHORTLIST_BLOCKED_DUPLICATE_HANDOFF'
            downstream_reason = 'DOWNSTREAM_ROUTE_REUSED_EXISTING_HANDOFF'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.WATCHLIST:
            reason = 'SHORTLIST_BLOCKED_LOW_PRIORITY'
            attempted = True
            downstream_reason = 'DOWNSTREAM_ROUTE_BLOCKED_BY_GUARDRAIL'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.DEFERRED:
            reason = 'SHORTLIST_BLOCKED_CONSENSUS_REQUIRED'
            attempted = True
            downstream_reason = 'DOWNSTREAM_ROUTE_BLOCKED_BY_GUARDRAIL'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.BLOCKED:
            reason = 'SHORTLIST_BLOCKED_BY_FILTER'
            attempted = True
            downstream_reason = 'DOWNSTREAM_ROUTE_BLOCKED_BY_GUARDRAIL'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.READY_FOR_RESEARCH:
            reason = 'SHORTLIST_ELIGIBLE_FOR_HANDOFF'
            attempted = True
            downstream_reason = 'DOWNSTREAM_ROUTE_AVAILABLE'
        else:
            reason = 'SHORTLIST_BLOCKED_BY_FILTER'
            downstream_reason = 'DOWNSTREAM_ROUTE_MISSING'

        if attempted:
            attempted_count += 1
        if created:
            created_count += 1
        if blocked:
            blocked_count += 1
        if market_id is not None:
            route_expected_count += 1
        if downstream_reason in {'DOWNSTREAM_ROUTE_AVAILABLE', 'DOWNSTREAM_ROUTE_CREATED_HANDOFF', 'DOWNSTREAM_ROUTE_REUSED_EXISTING_HANDOFF'}:
            route_available_count += 1
        if downstream_reason in {'DOWNSTREAM_ROUTE_MISSING', 'DOWNSTREAM_ROUTE_DISABLED', 'DOWNSTREAM_ROUTE_NO_ELIGIBLE_HANDLER'}:
            route_missing_count += 1
        if attempted:
            route_attempted_count += 1
        if created:
            route_created_count += 1
        if downstream_reason in {'DOWNSTREAM_ROUTE_BLOCKED_BY_GUARDRAIL', 'DOWNSTREAM_ROUTE_FILTERED_OUT'}:
            route_blocked_count += 1
        downstream_route_reason_codes.append(downstream_reason)
        shortlist_reason_codes.append(reason)
        if len(shortlist_examples) < 3:
            shortlist_examples.append({'signal_id': signal_id, 'market_id': market_id, 'reason_code': reason})
        if len(downstream_route_examples) < 3:
            downstream_route_examples.append(
                {
                    'signal_id': signal_id,
                    'market_id': market_id,
                    'expected_route': expected_route,
                    'reason_code': downstream_reason,
                }
            )

    shortlist_reason_codes = list(dict.fromkeys(shortlist_reason_codes))
    shortlist_handoff_summary = {
        **shortlist_handoff_summary,
        'handoff_attempted': int(attempted_count),
        'handoff_created': int(created_count),
        'handoff_blocked': int(blocked_count),
        'shortlist_handoff_reason_codes': shortlist_reason_codes,
        'shortlist_handoff_examples': shortlist_examples,
        'summary': (
            f"shortlisted_signals={shortlisted_count} handoff_attempted={attempted_count} handoff_created={created_count} "
            f"handoff_blocked={blocked_count} shortlist_handoff_reason_codes={','.join(shortlist_reason_codes) or 'none'}"
        ),
    }
    normalized_downstream_route_codes = list(dict.fromkeys(downstream_route_reason_codes))
    downstream_route_summary = {
        'route_expected': int(route_expected_count),
        'route_available': int(route_available_count),
        'route_missing': int(route_missing_count),
        'route_attempted': int(route_attempted_count),
        'route_created': int(route_created_count),
        'route_blocked': int(route_blocked_count),
        'downstream_route_reason_codes': normalized_downstream_route_codes,
        'downstream_route_summary': (
            f"route_expected={route_expected_count} route_available={route_available_count} "
            f"route_missing={route_missing_count} route_attempted={route_attempted_count} "
            f"route_created={route_created_count} route_blocked={route_blocked_count} "
            f"downstream_route_reason_codes={','.join(normalized_downstream_route_codes) or 'none'}"
        ),
    }
    operational_prediction_count = int(prediction_count)
    prediction_visibility_summary: dict[str, Any] = {}
    prediction_risk_summary: dict[str, Any] = {}

    if shortlisted_count > 0 and handoff_count == 0:
        handoff_reason_codes.append('SHORTLIST_PRESENT_NO_HANDOFF')
    if route_missing_count > 0:
        handoff_reason_codes.append('DOWNSTREAM_ROUTE_MISSING')
    if handoff_count > 0:
        handoff_reason_codes.append('HANDOFF_CREATED')
    if handoff_count > 0 and consensus_count == 0:
        handoff_reason_codes.append('CONSENSUS_NOT_RUN')
    if consensus_count > 0 and handoff_count > 0 and operational_prediction_count == 0:
        handoff_reason_codes.append('CONSENSUS_RAN_NO_PROMOTION')
    if handoff_count > 0 and operational_prediction_count == 0:
        handoff_reason_codes.append('PREDICTION_STAGE_EMPTY')
    if operational_prediction_count > 0 and risk_count == 0:
        handoff_reason_codes.append('RISK_STAGE_EMPTY')

    if shortlist_market_ids and handoff_market_ids:
        missing_from_handoff = sorted(shortlist_market_ids - handoff_market_ids)
        if missing_from_handoff:
            stage_source_mismatch['research_to_handoff_missing_market_ids'] = missing_from_handoff
    if handoff_market_ids and prediction_market_ids:
        missing_from_prediction = sorted(handoff_market_ids - prediction_market_ids)
        if missing_from_prediction:
            stage_source_mismatch['handoff_to_prediction_missing_market_ids'] = missing_from_prediction
    if prediction_market_ids and risk_market_ids:
        missing_from_risk = sorted(prediction_market_ids - risk_market_ids)
        if missing_from_risk:
            stage_source_mismatch['prediction_to_risk_missing_market_ids'] = missing_from_risk
    if stage_source_mismatch:
        handoff_reason_codes.append('FUNNEL_STAGE_SOURCE_MISMATCH')

    if shortlisted_count > 0 and operational_prediction_count == 0 and risk_count == 0 and paper_execution_count == 0:
        handoff_reason_codes.append('DOWNSTREAM_EVIDENCE_INSUFFICIENT')

    aligned_consensus_count = 0
    if shortlist_cluster_ids:
        aligned_consensus_count = NarrativeConsensusRecord.objects.filter(
            created_at__gte=window_start,
            linked_cluster_id__in=list(shortlist_cluster_ids),
        ).count()
    if consensus_count > 0 and aligned_consensus_count == 0:
        handoff_reason_codes.append('CONSENSUS_DECOUPLED_FROM_SHORTLIST')
    consensus_alignment = {
        'consensus_reviews': int(consensus_count),
        'shortlist_aligned_consensus_reviews': int(aligned_consensus_count),
        'consensus_aligned_with_shortlist': bool(consensus_count == 0 or aligned_consensus_count > 0),
    }

    handoff_rows = list(
        PredictionHandoffCandidate.objects.select_related('linked_consensus_record', 'linked_pursuit_score', 'linked_assessment')
        .filter(created_at__gte=window_start)
        .order_by('-created_at', '-id')[:40]
    )
    handoff_ready_count = 0
    handoff_deferred_count = 0
    handoff_blocked_count = 0
    handoff_status_reason_codes: list[str] = []
    deferred_reasons: list[str] = []
    handoff_scoring_examples: list[dict[str, Any]] = []
    borderline_handoff_count = 0
    borderline_promoted_count = 0
    borderline_blocked_count = 0
    borderline_reason_codes: list[str] = []
    handoff_borderline_examples: list[dict[str, Any]] = []
    structural_pass_count = 0
    structural_blocked_count = 0
    structural_override_enabled_count = 0
    structural_override_promoted_count = 0
    structural_override_blocked_count = 0
    structural_reason_codes: list[str] = []
    handoff_structural_examples: list[dict[str, Any]] = []
    for handoff in handoff_rows:
        status_reason_code, source_stage, observed_value, threshold, scoring_context = _handoff_status_reason(handoff=handoff)
        handoff_status_reason_codes.append(status_reason_code)
        if status_reason_code == 'HANDOFF_STATUS_DEFERRED_LOW_CONFIDENCE':
            handoff_status_reason_codes.append('HANDOFF_CONFIDENCE_BELOW_READY_THRESHOLD')
        if handoff.handoff_status == PredictionHandoffStatus.READY:
            handoff_ready_count += 1
        elif handoff.handoff_status == PredictionHandoffStatus.BLOCKED:
            handoff_blocked_count += 1
        else:
            handoff_deferred_count += 1
            deferred_reasons.append(status_reason_code)
        borderline = _evaluate_borderline_handoff(handoff=handoff, preset_name=preset_name)
        borderline_diagnostics_by_handoff[int(handoff.id)] = borderline
        structural_diagnostics = _evaluate_structural_guardrail(handoff=handoff, preset_name=preset_name)
        structural_reason_codes.append(str(structural_diagnostics.get('structural_reason_code') or 'HANDOFF_STRUCTURAL_WEAK_COMPOSITE'))
        if structural_diagnostics.get('override_enabled'):
            structural_override_enabled_count += 1
        if structural_diagnostics.get('override_applied'):
            structural_override_promoted_count += 1
        elif structural_diagnostics.get('blocked') and structural_diagnostics.get('override_enabled'):
            structural_override_blocked_count += 1
        if structural_diagnostics.get('blocked'):
            structural_blocked_count += 1
        else:
            structural_pass_count += 1
        if len(handoff_structural_examples) < 3:
            handoff_structural_examples.append(
                {
                    'handoff_id': int(handoff.id),
                    'market_id': _safe_int(handoff.linked_market_id),
                    'handoff_confidence': str(getattr(handoff, 'handoff_confidence', '') or ''),
                    'structural_status': structural_diagnostics.get('structural_status'),
                    'structural_reason_code': structural_diagnostics.get('structural_reason_code'),
                    'weak_components': structural_diagnostics.get('weak_components') or [],
                    'strong_components': structural_diagnostics.get('strong_components') or [],
                    'observed_values': structural_diagnostics.get('observed_values') or {},
                    'thresholds': structural_diagnostics.get('thresholds') or {},
                    'structural_rule_type': structural_diagnostics.get('structural_rule_type'),
                    'decision_source': str(structural_diagnostics.get('decision_source') or _BORDERLINE_DECISION_SOURCE),
                }
            )
        if borderline.get('reason_code') != 'HANDOFF_BORDERLINE_NOT_IN_BAND':
            borderline_handoff_count += 1
        borderline_reason_codes.append(str(borderline.get('reason_code') or 'HANDOFF_BORDERLINE_NOT_IN_BAND'))
        if borderline.get('eligible'):
            borderline_promoted_count += 1
            eligible_handoff_ids.add(int(handoff.id))
            borderline_reason_codes.append('HANDOFF_BORDERLINE_PROMOTED_TO_PREDICTION')
        elif borderline.get('reason_code') != 'HANDOFF_BORDERLINE_NOT_IN_BAND':
            borderline_blocked_count += 1
        if len(handoff_borderline_examples) < 3 and borderline.get('reason_code') != 'HANDOFF_BORDERLINE_NOT_IN_BAND':
            handoff_borderline_examples.append(
                {
                    'handoff_id': int(handoff.id),
                    'market_id': _safe_int(handoff.linked_market_id),
                    'handoff_confidence': str(getattr(handoff, 'handoff_confidence', '') or ''),
                    'ready_threshold': str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD),
                    'borderline_band': str(borderline.get('band') or ''),
                    'reason_code': str(borderline.get('reason_code') or ''),
                    'structural_reason_code': str(borderline.get('structural_reason_code') or ''),
                    'weak_components': list(borderline.get('weak_components') or []),
                    'observed_values': dict(borderline.get('observed_values') or {}),
                    'decision_source': str(borderline.get('decision_source') or _BORDERLINE_DECISION_SOURCE),
                }
            )
        if len(handoff_scoring_examples) < _HANDOFF_SCORING_EXAMPLES_LIMIT:
            handoff_scoring_examples.append(
                {
                    'handoff_id': int(handoff.id),
                    'market_id': _safe_int(handoff.linked_market_id),
                    'handoff_status': str(getattr(handoff, 'handoff_status', '') or ''),
                    'handoff_confidence': str(getattr(handoff, 'handoff_confidence', '') or ''),
                    'status_reason_code': status_reason_code,
                    'scoring_components': scoring_context.get('score_components') or {},
                    'score_status': scoring_context.get('score_status'),
                    'structural_status': scoring_context.get('structural_status'),
                    'observed_value': observed_value,
                    'threshold': threshold,
                    'source_stage': source_stage,
                }
            )
    handoff_status_reason_codes = list(dict.fromkeys(handoff_status_reason_codes))
    deferred_reasons = list(dict.fromkeys(deferred_reasons))
    borderline_reason_codes = list(dict.fromkeys(borderline_reason_codes))
    handoff_borderline_summary = {
        'borderline_handoffs': int(borderline_handoff_count),
        'borderline_promoted': int(borderline_promoted_count),
        'borderline_blocked': int(borderline_blocked_count),
        'borderline_reason_codes': borderline_reason_codes,
        'ready_threshold': str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD),
        'borderline_band': f'[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX})',
        'borderline_summary': (
            f"borderline_handoffs={borderline_handoff_count} borderline_promoted={borderline_promoted_count} "
            f"borderline_blocked={borderline_blocked_count} ready_threshold={_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD} "
            f"borderline_band=[{_BORDERLINE_CONFIDENCE_MIN},{_BORDERLINE_CONFIDENCE_MAX}) "
            f"borderline_reason_codes={','.join(borderline_reason_codes) or 'none'}"
        ),
    }
    structural_reason_codes = list(dict.fromkeys(structural_reason_codes))
    handoff_structural_summary = {
        'structural_pass': int(structural_pass_count),
        'structural_blocked': int(structural_blocked_count),
        'structural_weakness_count': int(structural_blocked_count),
        'structural_pass_count': int(structural_pass_count),
        'structural_reason_codes': structural_reason_codes,
        'structural_block_reason_codes': [code for code in structural_reason_codes if code != 'HANDOFF_STRUCTURAL_PASS'],
        'override_enabled': int(structural_override_enabled_count),
        'override_promoted': int(structural_override_promoted_count),
        'override_blocked': int(structural_override_blocked_count),
        'structural_guardrail_summary': (
            f"structural_pass={structural_pass_count} structural_blocked={structural_blocked_count} "
            f"override_enabled={structural_override_enabled_count} override_promoted={structural_override_promoted_count} "
            f"override_blocked={structural_override_blocked_count} "
            f"structural_reason_codes={','.join(structural_reason_codes) or 'none'}"
        ),
    }
    handoff_scoring_summary = {
        'handoff_ready': int(handoff_ready_count),
        'handoff_deferred': int(handoff_deferred_count),
        'handoff_blocked': int(handoff_blocked_count),
        'handoff_status_reason_codes': handoff_status_reason_codes,
        'ready_threshold': str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD),
        'deferred_reasons': deferred_reasons,
        'handoff_scoring_summary': (
            f"handoff_ready={handoff_ready_count} handoff_deferred={handoff_deferred_count} handoff_blocked={handoff_blocked_count} "
            f"ready_threshold={_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD} "
            f"handoff_status_reason_codes={','.join(handoff_status_reason_codes) or 'none'} "
            f"deferred_reasons={','.join(deferred_reasons) or 'none'}"
        ),
    }
    existing_intake_handoff_ids = {
        int(handoff_id)
        for handoff_id in PredictionIntakeCandidate.objects.filter(
            linked_prediction_handoff_candidate_id__in=list(eligible_handoff_ids)
        ).values_list('linked_prediction_handoff_candidate_id', flat=True)
        if handoff_id is not None
    }
    if handoff_count > 0 and prediction_count == 0 and route_available and eligible_handoff_ids and not existing_intake_handoff_ids:
        bridge_attempted = True
        run_prediction_intake_review(triggered_by='mission_control_prediction_bridge')
        prediction_qs = PredictionConvictionReview.objects.filter(created_at__gte=window_start)
        intake_run_qs = PredictionIntakeRun.objects.filter(created_at__gte=window_start)
        intake_candidate_qs = PredictionIntakeCandidate.objects.filter(created_at__gte=window_start)
        prediction_count = prediction_qs.count()
        intake_run_count = intake_run_qs.count()
        intake_candidate_count = intake_candidate_qs.count()
        intake_after_ids = {
            int(handoff_id)
            for handoff_id in PredictionIntakeCandidate.objects.filter(
                linked_prediction_handoff_candidate_id__in=list(eligible_handoff_ids)
            ).values_list('linked_prediction_handoff_candidate_id', flat=True)
            if handoff_id is not None
        }
        bridge_created_handoff_ids = intake_after_ids - existing_intake_handoff_ids

    handoff_ids = [handoff.id for handoff in handoff_rows]
    intake_candidate_by_handoff = set(
        PredictionIntakeCandidate.objects.filter(linked_prediction_handoff_candidate_id__in=handoff_ids)
        .exclude(linked_prediction_handoff_candidate_id__isnull=True)
        .values_list('linked_prediction_handoff_candidate_id', flat=True)
    )
    prediction_intake_attempted = 0
    prediction_intake_created = 0
    prediction_intake_blocked = 0
    prediction_intake_missing_fields = 0
    prediction_intake_guardrail_blocked = 0
    prediction_intake_eligible_count = 0
    prediction_intake_ineligible_count = 0
    prediction_intake_reused_count = 0
    prediction_intake_guardrail_reason_codes: list[str] = []
    prediction_intake_filter_reason_codes: list[str] = []

    for handoff in handoff_rows:
        diagnosis: dict[str, Any] = {
            'reason_code': 'PREDICTION_INTAKE_FILTER_REJECTED',
            'reason_type': 'filter',
            'guardrail_name': None,
            'filter_name': None,
            'observed_value': None,
            'threshold': None,
            'blocking_stage': 'mission_control_precheck',
        }
        missing_fields = _missing_prediction_intake_fields(handoff=handoff)
        if route_available:
            prediction_intake_reason_codes.append('PREDICTION_INTAKE_ROUTE_AVAILABLE')
        if handoff.id in intake_candidate_by_handoff:
            prediction_intake_attempted += 1
            prediction_intake_created += 1
            prediction_intake_eligible_count += 1
            if handoff.id in bridge_created_handoff_ids:
                reason_code = 'PREDICTION_INTAKE_CREATED'
            else:
                reason_code = 'PREDICTION_INTAKE_REUSED_EXISTING_CANDIDATE'
                prediction_intake_reused_count += 1
            prediction_intake_reason_codes.append('PREDICTION_INTAKE_ELIGIBLE')
            prediction_intake_reason_codes.append(reason_code)
            if len(prediction_intake_examples) < 3:
                prediction_intake_examples.append(
                    {
                        'handoff_id': handoff.id,
                        'signal_id': None,
                        'market_id': _safe_int(handoff.linked_market_id),
                        'handoff_status': str(getattr(handoff, 'handoff_status', '') or ''),
                        'handoff_confidence': str(getattr(handoff, 'handoff_confidence', '') or ''),
                        'expected_route': _PREDICTION_INTAKE_ROUTE_NAME,
                        'reason_code': reason_code,
                        'blocking_stage': 'existing_candidate',
                        'guardrail_name': None,
                        'filter_name': 'existing_candidate_reuse',
                        'observed_value': handoff.id,
                        'threshold': None,
                        'missing_fields': [],
                    }
                )
            continue

        if prediction_intake_route_disabled:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_ROUTE_MISSING',
                reason_type='guardrail',
                guardrail_name='prediction_intake_route_enabled',
                observed_value=False,
                threshold=True,
            )
            prediction_intake_blocked += 1
        elif not prediction_intake_handler_available:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_NO_ELIGIBLE_HANDLER',
                reason_type='guardrail',
                guardrail_name='prediction_intake_handler_available',
                observed_value=False,
                threshold=True,
            )
            prediction_intake_blocked += 1
        elif missing_fields:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_MISSING_REQUIRED_FIELDS',
                reason_type='guardrail',
                guardrail_name='prediction_intake_required_fields',
                observed_value=missing_fields,
                threshold='[]',
            )
            prediction_intake_blocked += 1
            prediction_intake_missing_fields += 1
        elif handoff.handoff_status in {PredictionHandoffStatus.BLOCKED, PredictionHandoffStatus.DEFERRED}:
            borderline = borderline_diagnostics_by_handoff.get(int(handoff.id), {})
            if handoff.handoff_status == PredictionHandoffStatus.DEFERRED and borderline.get('eligible'):
                diagnosis.update(
                    reason_code='PREDICTION_INTAKE_ENABLED_BY_BORDERLINE_PROMOTION',
                    reason_type='filter',
                    filter_name='borderline_handoff_promotion',
                    observed_value=str(getattr(handoff, 'handoff_confidence', None)),
                    threshold=str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD),
                    blocking_stage='mission_control_borderline',
                )
            else:
                diagnosis.update(
                    reason_code='PREDICTION_INTAKE_GUARDRAIL_REJECTED',
                    reason_type='guardrail',
                    guardrail_name='handoff_status_guardrail',
                    observed_value=handoff.handoff_status,
                    threshold='READY',
                )
                prediction_intake_blocked += 1
                prediction_intake_guardrail_blocked += 1
        elif getattr(handoff, 'linked_market_id', None) is None or getattr(getattr(handoff, 'linked_market', None), 'current_market_probability', None) is None:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_MARKET_PROBABILITY_MISSING',
                reason_type='filter',
                filter_name='market_probability_presence',
                observed_value=getattr(getattr(handoff, 'linked_market', None), 'current_market_probability', None),
                threshold='not_none',
            )
            prediction_intake_blocked += 1
        elif handoff.handoff_confidence is None or Decimal(str(handoff.handoff_confidence)) < _PREDICTION_INTAKE_CONFIDENCE_THRESHOLD:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_CONFIDENCE_BELOW_THRESHOLD',
                reason_type='filter',
                filter_name='handoff_confidence_threshold',
                observed_value=str(getattr(handoff, 'handoff_confidence', None)),
                threshold=str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD),
            )
            prediction_intake_blocked += 1
        elif handoff.handoff_status != PredictionHandoffStatus.READY:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_HANDOFF_STATUS_INELIGIBLE',
                reason_type='filter',
                filter_name='handoff_status_eligibility',
                observed_value=handoff.handoff_status,
                threshold=PredictionHandoffStatus.READY,
            )
            prediction_intake_blocked += 1
        elif handoff.linked_consensus_record_id is None and consensus_count > 0:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_FILTER_REJECTED',
                reason_type='filter',
                filter_name='consensus_link_required_when_consensus_exists',
                observed_value=False,
                threshold=True,
            )
            prediction_intake_blocked += 1
        elif bridge_attempted:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_RECENT_DEDUPE_ACTIVE',
                reason_type='filter',
                filter_name='recent_intake_dedupe_window',
                observed_value=True,
                threshold=False,
                blocking_stage='handler_internal',
            )
            prediction_intake_attempted += 1
            prediction_intake_blocked += 1
        else:
            diagnosis.update(
                reason_code='PREDICTION_INTAKE_FILTER_REJECTED',
                reason_type='filter',
                filter_name='fallback_eligibility_filter',
            )
            prediction_intake_blocked += 1
        reason_code = diagnosis['reason_code']
        if diagnosis['reason_type'] == 'guardrail':
            prediction_intake_guardrail_reason_codes.append(reason_code)
        else:
            prediction_intake_filter_reason_codes.append(reason_code)
        prediction_intake_ineligible_count += 1
        prediction_intake_reason_codes.append(reason_code)
        if len(prediction_intake_examples) < 3:
            prediction_intake_examples.append(
                {
                    'handoff_id': handoff.id,
                    'signal_id': None,
                    'market_id': _safe_int(handoff.linked_market_id),
                    'handoff_status': str(getattr(handoff, 'handoff_status', '') or ''),
                    'handoff_confidence': str(getattr(handoff, 'handoff_confidence', '') or ''),
                    'expected_route': _PREDICTION_INTAKE_ROUTE_NAME,
                    'reason_code': reason_code,
                    'blocking_stage': diagnosis.get('blocking_stage'),
                    'guardrail_name': diagnosis.get('guardrail_name'),
                    'filter_name': diagnosis.get('filter_name'),
                    'observed_value': diagnosis.get('observed_value'),
                    'threshold': diagnosis.get('threshold'),
                    'missing_fields': missing_fields,
                }
            )

    if bridge_attempted:
        prediction_intake_reason_codes.append('PREDICTION_INTAKE_ATTEMPTED')
    if prediction_intake_created > 0:
        prediction_intake_reason_codes.append('PREDICTION_INTAKE_CREATED')
    if prediction_intake_attempted == 0 and handoff_count > 0:
        if route_available:
            if not prediction_intake_filter_reason_codes and not prediction_intake_guardrail_reason_codes:
                prediction_intake_filter_reason_codes.append('PREDICTION_INTAKE_FILTER_REJECTED')
                prediction_intake_reason_codes.append('PREDICTION_INTAKE_FILTER_REJECTED')
        else:
            prediction_intake_reason_codes.append('PREDICTION_INTAKE_ROUTE_MISSING')
    prediction_intake_guardrail_reason_codes = list(dict.fromkeys(prediction_intake_guardrail_reason_codes))
    prediction_intake_filter_reason_codes = list(dict.fromkeys(prediction_intake_filter_reason_codes))
    prediction_intake_summary = {
        'handoff_candidates': int(handoff_count),
        'prediction_intake_attempted': int(prediction_intake_attempted),
        'prediction_intake_created': int(prediction_intake_created),
        'prediction_intake_blocked': int(prediction_intake_blocked),
        'prediction_intake_missing_fields': int(prediction_intake_missing_fields),
        'prediction_intake_guardrail_blocked': int(prediction_intake_guardrail_blocked),
        'prediction_intake_eligible_count': int(prediction_intake_eligible_count),
        'prediction_intake_ineligible_count': int(prediction_intake_ineligible_count),
        'prediction_intake_reused_count': int(prediction_intake_reused_count),
        'prediction_intake_reason_codes': list(dict.fromkeys(prediction_intake_reason_codes)),
        'prediction_intake_guardrail_reason_codes': prediction_intake_guardrail_reason_codes,
        'prediction_intake_filter_reason_codes': prediction_intake_filter_reason_codes,
        'prediction_intake_guardrail_summary': (
            f"guardrail_blocked={prediction_intake_guardrail_blocked} "
            f"guardrail_reasons={','.join(prediction_intake_guardrail_reason_codes) or 'none'} "
            f"filter_reasons={','.join(prediction_intake_filter_reason_codes) or 'none'}"
        ),
        'prediction_intake_summary': (
            f"handoff_candidates={handoff_count} prediction_intake_attempted={prediction_intake_attempted} "
            f"prediction_intake_created={prediction_intake_created} prediction_intake_blocked={prediction_intake_blocked} "
            f"prediction_intake_eligible_count={prediction_intake_eligible_count} "
            f"prediction_intake_ineligible_count={prediction_intake_ineligible_count} "
            f"prediction_intake_reused_count={prediction_intake_reused_count} "
            f"prediction_intake_missing_fields={prediction_intake_missing_fields} "
            f"prediction_intake_guardrail_blocked={prediction_intake_guardrail_blocked} "
            f"prediction_intake_reason_codes={','.join(list(dict.fromkeys(prediction_intake_reason_codes))) or 'none'}"
        ),
    }

    intake_candidate_rows = list(
        PredictionIntakeCandidate.objects.filter(linked_prediction_handoff_candidate_id__in=[handoff.id for handoff in handoff_rows]).order_by('-created_at', '-id')
    )
    conviction_by_candidate_id = {}
    for review in (
        PredictionConvictionReview.objects.filter(linked_intake_candidate_id__in=[candidate.id for candidate in intake_candidate_rows])
        .order_by('linked_intake_candidate_id', '-created_at', '-id')
    ):
        if review.linked_intake_candidate_id not in conviction_by_candidate_id:
            conviction_by_candidate_id[int(review.linked_intake_candidate_id)] = review
    visible_candidates_for_artifacts = [
        candidate
        for candidate in intake_candidate_rows
        if candidate.intake_status in {PredictionIntakeStatus.READY_FOR_RUNTIME, PredictionIntakeStatus.MONITOR_ONLY}
    ]
    (
        prediction_artifact_summary,
        conviction_by_candidate_id,
        handoff_by_candidate_id,
        artifact_route_resolved_candidate_ids,
    ) = _materialize_prediction_artifacts_for_risk(
        candidates=visible_candidates_for_artifacts,
        conviction_by_candidate_id=conviction_by_candidate_id,
    )

    prediction_intake_created_count = 0
    prediction_intake_reused_count = 0
    prediction_candidates_visible_count = 0
    prediction_candidates_hidden_count = 0
    prediction_visibility_reason_codes = []
    prediction_risk_reason_codes = []
    prediction_risk_examples: list[dict[str, Any]] = []
    prediction_status_reason_codes: list[str] = []
    prediction_status_examples: list[dict[str, Any]] = []
    prediction_visibility_examples = []
    visible_candidate_ids = []
    risk_route_eligible_candidate_ids: list[int] = []
    risk_route_missing_status_count = 0
    risk_route_blocked = 0
    risk_route_created = 0
    risk_route_reused_existing_decision = 0
    prediction_status_monitor_only_count = 0
    prediction_status_ready_for_runtime_count = 0
    prediction_status_blocked_count = 0
    monitor_only_candidates = 0
    risk_with_caution_eligible_count = 0
    risk_with_caution_promoted_count = 0
    risk_with_caution_blocked_count = 0
    risk_with_caution_reason_codes: list[str] = []
    prediction_risk_caution_examples: list[dict[str, Any]] = []
    caution_eligible_candidate_ids: list[int] = []
    caution_promoted_candidate_ids: list[int] = []
    prediction_risk_route_disabled = _is_prediction_risk_route_disabled()
    prediction_risk_handler_available = _is_prediction_risk_handler_available()
    for candidate in intake_candidate_rows:
        source = 'created' if candidate.created_at >= window_start else 'reused'
        if source == 'created':
            prediction_intake_created_count += 1
        else:
            prediction_intake_reused_count += 1
        visible = candidate.intake_status in {PredictionIntakeStatus.READY_FOR_RUNTIME, PredictionIntakeStatus.MONITOR_ONLY}
        if visible:
            prediction_candidates_visible_count += 1
            visible_candidate_ids.append(int(candidate.id))
            visibility_reason = 'PREDICTION_REUSED_BUT_NOT_COUNTED' if source == 'reused' else 'PREDICTION_VISIBLE_IN_FUNNEL'
        else:
            prediction_candidates_hidden_count += 1
            visibility_reason = 'PREDICTION_HIDDEN_BY_STATUS_FILTER'
        prediction_visibility_reason_codes.append(visibility_reason)

        candidate_id = int(candidate.id)
        linked_review = conviction_by_candidate_id.get(candidate_id)
        linked_handoff = handoff_by_candidate_id.get(candidate_id)
        status_reason_details = _derive_prediction_status_reason(candidate=candidate, linked_review=linked_review, source=source)
        prediction_status_reason_codes.append(status_reason_details['status_reason_code'])
        if candidate.intake_status == PredictionIntakeStatus.MONITOR_ONLY:
            prediction_status_monitor_only_count += 1
        elif candidate.intake_status == PredictionIntakeStatus.READY_FOR_RUNTIME:
            prediction_status_ready_for_runtime_count += 1
        else:
            prediction_status_blocked_count += 1
        if len(prediction_status_examples) < _PREDICTION_STATUS_EXAMPLES_LIMIT:
            prediction_status_examples.append(
                {
                    'candidate_id': int(candidate.id),
                    'market_id': _safe_int(candidate.linked_market_id),
                    'prediction_status': str(candidate.intake_status or ''),
                    'status_reason_code': status_reason_details['status_reason_code'],
                    'confidence': str(candidate.handoff_confidence),
                    'edge': str(candidate.structural_priority),
                    'uncertainty': str(getattr(linked_review, 'uncertainty', '')) if linked_review else '',
                    'source_stage': status_reason_details['source_stage'],
                    'observed_value': status_reason_details['observed_value'],
                    'threshold': status_reason_details['threshold'],
                    'lineage_summary': (
                        f"handoff={(candidate.metadata or {}).get('handoff_status', '')} "
                        f"pursuit={(candidate.metadata or {}).get('pursuit_priority_bucket', '')} "
                        f"consensus={'yes' if candidate.linked_consensus_record_id else 'no'} "
                        f"reuse={source}"
                    ),
                }
            )
        risk_reason_code = 'PREDICTION_RISK_ROUTE_MISSING'
        blocking_stage = 'prediction_to_risk_bridge'
        observed_value: Any = str(candidate.intake_status or '')
        threshold: Any = PredictionConvictionReviewStatus.READY_FOR_RISK
        caution_diagnostics: dict[str, Any] | None = None
        if candidate.intake_status == PredictionIntakeStatus.MONITOR_ONLY:
            monitor_only_candidates += 1
            caution_diagnostics = _evaluate_prediction_risk_with_caution(
                candidate=candidate,
                linked_review=linked_review,
                preset_name=preset_name,
            )
            risk_with_caution_reason_codes.append(str(caution_diagnostics.get('reason_code') or ''))
            if caution_diagnostics.get('eligible'):
                risk_with_caution_eligible_count += 1
                caution_eligible_candidate_ids.append(int(candidate.id))
            else:
                risk_with_caution_blocked_count += 1
            if len(prediction_risk_caution_examples) < _PREDICTION_RISK_CAUTION_EXAMPLES_LIMIT:
                prediction_risk_caution_examples.append(
                    {
                        'candidate_id': int(candidate.id),
                        'market_id': _safe_int(candidate.linked_market_id),
                        'confidence': str(caution_diagnostics.get('confidence', '')),
                        'edge': str(caution_diagnostics.get('edge', '')),
                        'runtime_ready_threshold': caution_diagnostics.get('runtime_ready_threshold'),
                        'caution_band': caution_diagnostics.get('caution_band'),
                        'reason_code': caution_diagnostics.get('reason_code'),
                        'decision_source': caution_diagnostics.get('decision_source'),
                    }
                )
        if not visible:
            risk_reason_code = 'PREDICTION_RISK_STATUS_FILTER_REJECTED'
            blocking_stage = 'prediction_visibility'
            risk_route_missing_status_count += 1
            risk_route_blocked += 1
        elif prediction_risk_route_disabled:
            risk_reason_code = 'PREDICTION_RISK_ROUTE_MISSING'
            blocking_stage = 'mission_control_guardrail'
            observed_value = False
            threshold = True
            risk_route_blocked += 1
        elif not prediction_risk_handler_available:
            risk_reason_code = 'PREDICTION_RISK_NO_ELIGIBLE_HANDLER'
            blocking_stage = 'mission_control_handler_lookup'
            observed_value = False
            threshold = True
            risk_route_blocked += 1
        elif candidate.intake_status == PredictionIntakeStatus.MONITOR_ONLY:
            if caution_diagnostics and caution_diagnostics.get('eligible'):
                if not linked_review:
                    risk_reason_code = 'PREDICTION_RISK_ROUTE_MISSING'
                    blocking_stage = 'prediction_artifact_mismatch'
                    observed_value = 'PredictionIntakeCandidate'
                    threshold = 'PredictionConvictionReview'
                    risk_route_blocked += 1
                    if len(prediction_artifact_summary.get('prediction_artifact_examples') or []) < 3:
                        prediction_artifact_summary['prediction_artifact_examples'].append(
                            {
                                'candidate_id': candidate_id,
                                'market_id': _safe_int(candidate.linked_market_id),
                                'source_model': 'PredictionIntakeCandidate',
                                'expected_artifact': 'PredictionConvictionReview',
                                'created_artifact': None,
                                'reused_artifact': None,
                                'reason_code': 'PREDICTION_ARTIFACT_MISMATCH_BLOCKED',
                                'blocking_stage': 'prediction_artifact_mismatch',
                            }
                        )
                elif linked_review.review_status != PredictionConvictionReviewStatus.READY_FOR_RISK:
                    risk_reason_code = 'PREDICTION_RISK_STATUS_FILTER_REJECTED'
                    blocking_stage = 'prediction_conviction_review'
                    observed_value = str(linked_review.review_status or '')
                    threshold = PredictionConvictionReviewStatus.READY_FOR_RISK
                    risk_route_missing_status_count += 1
                    risk_route_blocked += 1
                else:
                    risk_reason_code = 'PREDICTION_RISK_WITH_CAUTION_PROMOTED'
                    blocking_stage = 'prediction_risk_with_caution_precheck'
                    observed_value = str(linked_review.review_status or '')
                    threshold = PredictionConvictionReviewStatus.READY_FOR_RISK
                    risk_route_eligible_candidate_ids.append(int(candidate.id))
                    risk_with_caution_promoted_count += 1
                    caution_promoted_candidate_ids.append(int(candidate.id))
                    risk_with_caution_reason_codes.append('PREDICTION_RISK_WITH_CAUTION_PROMOTED')
            else:
                risk_reason_code = str((caution_diagnostics or {}).get('reason_code') or 'PREDICTION_RISK_STATUS_FILTER_REJECTED')
                blocking_stage = 'prediction_risk_with_caution_precheck'
                observed_value = str(candidate.handoff_confidence)
                threshold = (caution_diagnostics or {}).get('caution_band') or PredictionIntakeStatus.READY_FOR_RUNTIME
                risk_route_missing_status_count += 1
                risk_route_blocked += 1
        elif not linked_review:
            risk_reason_code = 'PREDICTION_RISK_ROUTE_MISSING'
            blocking_stage = 'prediction_artifact_mismatch'
            observed_value = 'PredictionIntakeCandidate'
            threshold = 'PredictionConvictionReview'
            risk_route_blocked += 1
            if len(prediction_artifact_summary.get('prediction_artifact_examples') or []) < 3:
                prediction_artifact_summary['prediction_artifact_examples'].append(
                    {
                        'candidate_id': candidate_id,
                        'market_id': _safe_int(candidate.linked_market_id),
                        'source_model': 'PredictionIntakeCandidate',
                        'expected_artifact': 'PredictionConvictionReview',
                        'created_artifact': None,
                        'reused_artifact': None,
                        'reason_code': 'PREDICTION_ARTIFACT_MISMATCH_BLOCKED',
                        'blocking_stage': 'prediction_artifact_mismatch',
                    }
                )
        elif linked_review.review_status != PredictionConvictionReviewStatus.READY_FOR_RISK:
            risk_reason_code = 'PREDICTION_RISK_STATUS_FILTER_REJECTED'
            blocking_stage = 'prediction_conviction_review'
            observed_value = str(linked_review.review_status or '')
            threshold = PredictionConvictionReviewStatus.READY_FOR_RISK
            risk_route_missing_status_count += 1
            risk_route_blocked += 1
        elif linked_handoff is None:
            risk_reason_code = 'PREDICTION_RISK_ROUTE_MISSING'
            blocking_stage = 'prediction_artifact_mismatch'
            observed_value = 'PredictionConvictionReview'
            threshold = 'RiskReadyPredictionHandoff'
            risk_route_blocked += 1
            if len(prediction_artifact_summary.get('prediction_artifact_examples') or []) < 3:
                prediction_artifact_summary['prediction_artifact_examples'].append(
                    {
                        'candidate_id': candidate_id,
                        'market_id': _safe_int(candidate.linked_market_id),
                        'source_model': 'PredictionConvictionReview',
                        'expected_artifact': 'RiskReadyPredictionHandoff',
                        'created_artifact': None,
                        'reused_artifact': None,
                        'reason_code': 'PREDICTION_ARTIFACT_MISMATCH_BLOCKED',
                        'blocking_stage': 'prediction_artifact_mismatch',
                    }
                )
        else:
            risk_reason_code = 'PREDICTION_RISK_ROUTE_AVAILABLE'
            blocking_stage = 'risk_runtime_precheck'
            observed_value = str(linked_review.review_status or '')
            threshold = PredictionConvictionReviewStatus.READY_FOR_RISK
            risk_route_eligible_candidate_ids.append(int(candidate.id))
        prediction_risk_reason_codes.append(risk_reason_code)
        if len(prediction_risk_examples) < 3:
            prediction_risk_examples.append(
                {
                    'candidate_id': int(candidate.id),
                    'market_id': _safe_int(candidate.linked_market_id),
                    'source_model': 'PredictionIntakeCandidate',
                    'prediction_status': str(candidate.intake_status or ''),
                    'expected_route': _PREDICTION_RISK_ROUTE_NAME,
                    'reason_code': risk_reason_code,
                    'blocking_stage': blocking_stage,
                    'observed_value': observed_value,
                    'threshold': threshold,
                }
            )
        if len(prediction_visibility_examples) < 3:
            prediction_visibility_examples.append(
                {
                    'candidate_id': int(candidate.id),
                    'handoff_id': _safe_int(candidate.linked_prediction_handoff_candidate_id),
                    'market_id': _safe_int(candidate.linked_market_id),
                    'source': source,
                    'source_model': 'PredictionIntakeCandidate',
                    'source_stage': 'prediction_intake',
                    'visible_in_funnel': bool(visible),
                    'reason_code': visibility_reason,
                    'visibility_window': 'current_window' if source == 'created' else 'outside_window_reused',
                    'status': str(candidate.intake_status or ''),
                }
            )

    preexisting_risk_decision_candidate_ids = set(
        int(candidate_id)
        for candidate_id in RiskApprovalDecision.objects.filter(
            linked_candidate__linked_prediction_intake_candidate_id__in=visible_candidate_ids
        ).values_list('linked_candidate__linked_prediction_intake_candidate_id', flat=True)
        if candidate_id is not None
    )
    eligible_without_decision_ids = [candidate_id for candidate_id in risk_route_eligible_candidate_ids if candidate_id not in preexisting_risk_decision_candidate_ids]
    risk_route_attempted = 0
    if eligible_without_decision_ids and not prediction_risk_route_disabled and prediction_risk_handler_available:
        risk_route_attempted = len(eligible_without_decision_ids)
        prediction_risk_reason_codes.append('PREDICTION_RISK_ATTEMPTED')
        run_risk_runtime_review(triggered_by='mission_control_prediction_risk_bridge')

    current_risk_decision_candidate_ids = set(
        int(candidate_id)
        for candidate_id in RiskApprovalDecision.objects.filter(
            linked_candidate__linked_prediction_intake_candidate_id__in=visible_candidate_ids
        ).values_list('linked_candidate__linked_prediction_intake_candidate_id', flat=True)
        if candidate_id is not None
    )
    created_risk_decision_candidate_ids = current_risk_decision_candidate_ids - preexisting_risk_decision_candidate_ids
    risk_route_created = len([candidate_id for candidate_id in risk_route_eligible_candidate_ids if candidate_id in created_risk_decision_candidate_ids])
    risk_route_reused_existing_decision = len(
        [candidate_id for candidate_id in risk_route_eligible_candidate_ids if candidate_id in preexisting_risk_decision_candidate_ids]
    )
    if risk_route_created > 0:
        prediction_risk_reason_codes.append('PREDICTION_RISK_CREATED')
    if risk_route_reused_existing_decision > 0:
        prediction_risk_reason_codes.append('PREDICTION_RISK_REUSED_EXISTING_DECISION')
    if any(candidate_id in preexisting_risk_decision_candidate_ids for candidate_id in caution_promoted_candidate_ids):
        risk_with_caution_reason_codes.append('PREDICTION_RISK_WITH_CAUTION_REUSED')

    risk_route_expected = int(prediction_candidates_visible_count)
    risk_route_available = int(len(risk_route_eligible_candidate_ids))
    risk_route_decision_count_window = RiskApprovalDecision.objects.filter(
        linked_candidate__linked_prediction_intake_candidate_id__in=visible_candidate_ids,
        created_at__gte=window_start,
    ).count()
    risk_route_blocked = max(0, risk_route_expected - (risk_route_created + risk_route_reused_existing_decision))
    prediction_artifact_summary['prediction_artifact_blocked_count'] = max(
        0,
        int(prediction_artifact_summary.get('prediction_artifact_expected_count', 0)) - int(len(artifact_route_resolved_candidate_ids)),
    )
    if prediction_artifact_summary['prediction_artifact_blocked_count'] > 0:
        prediction_artifact_summary['prediction_artifact_reason_codes'] = list(
            dict.fromkeys(
                list(prediction_artifact_summary.get('prediction_artifact_reason_codes') or [])
                + ['PREDICTION_ARTIFACT_MISMATCH_BLOCKED']
            )
        )
    prediction_artifact_summary['prediction_artifact_summary'] = (
        f"artifact_expected={prediction_artifact_summary.get('prediction_artifact_expected_count', 0)} "
        f"conviction_review_available={prediction_artifact_summary.get('conviction_review_available_count', 0)} "
        f"conviction_review_created={prediction_artifact_summary.get('conviction_review_created_count', 0)} "
        f"conviction_review_reused={prediction_artifact_summary.get('conviction_review_reused_count', 0)} "
        f"risk_ready_handoff_available={prediction_artifact_summary.get('risk_ready_handoff_available_count', 0)} "
        f"risk_ready_handoff_created={prediction_artifact_summary.get('risk_ready_handoff_created_count', 0)} "
        f"risk_ready_handoff_reused={prediction_artifact_summary.get('risk_ready_handoff_reused_count', 0)} "
        f"artifact_blocked={prediction_artifact_summary.get('prediction_artifact_blocked_count', 0)} "
        f"prediction_artifact_reason_codes={','.join(prediction_artifact_summary.get('prediction_artifact_reason_codes') or []) or 'none'}"
    )
    prediction_risk_summary = {
        'risk_route_expected': int(risk_route_expected),
        'risk_route_available': int(risk_route_available),
        'risk_route_attempted': int(risk_route_attempted),
        'risk_route_created': int(risk_route_created),
        'risk_route_blocked': int(risk_route_blocked),
        'risk_route_missing_status_count': int(risk_route_missing_status_count),
        'risk_route_runtime_decisions_window': int(risk_route_decision_count_window),
        'risk_route_reason_codes': list(dict.fromkeys(prediction_risk_reason_codes)),
        'risk_route_summary': (
            f"risk_route_expected={risk_route_expected} risk_route_available={risk_route_available} "
            f"risk_route_attempted={risk_route_attempted} risk_route_created={risk_route_created} "
            f"risk_route_blocked={risk_route_blocked} risk_route_missing_status_count={risk_route_missing_status_count} "
            f"risk_route_reason_codes={','.join(list(dict.fromkeys(prediction_risk_reason_codes))) or 'none'}"
        ),
    }
    if prediction_artifact_summary.get('risk_ready_handoff_created_count', 0) > 0:
        prediction_risk_summary['risk_route_reason_codes'] = list(
            dict.fromkeys(list(prediction_risk_summary.get('risk_route_reason_codes') or []) + ['PREDICTION_ARTIFACT_MISMATCH_RESOLVED'])
        )
    prediction_risk_caution_summary = {
        'monitor_only_candidates': int(monitor_only_candidates),
        'risk_with_caution_eligible_count': int(risk_with_caution_eligible_count),
        'risk_with_caution_promoted_count': int(risk_with_caution_promoted_count),
        'risk_with_caution_blocked_count': int(risk_with_caution_blocked_count),
        'risk_with_caution_reason_codes': list(dict.fromkeys([code for code in risk_with_caution_reason_codes if code])),
        'runtime_ready_threshold': str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD),
        'caution_band': f'[{_PREDICTION_RISK_CAUTION_BAND_MIN},{_PREDICTION_RISK_CAUTION_BAND_MAX})',
        'risk_with_caution_summary': (
            f"monitor_only_candidates={monitor_only_candidates} "
            f"risk_with_caution_eligible={risk_with_caution_eligible_count} "
            f"risk_with_caution_promoted={risk_with_caution_promoted_count} "
            f"risk_with_caution_blocked={risk_with_caution_blocked_count} "
            f"risk_with_caution_reason_codes={','.join(list(dict.fromkeys([code for code in risk_with_caution_reason_codes if code]))) or 'none'}"
        ),
    }
    runtime_ready_threshold = str(_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD)
    prediction_status_summary = {
        'prediction_status_monitor_only_count': int(prediction_status_monitor_only_count),
        'prediction_status_ready_for_runtime_count': int(prediction_status_ready_for_runtime_count),
        'prediction_status_blocked_count': int(prediction_status_blocked_count),
        'prediction_status_reason_codes': list(dict.fromkeys(prediction_status_reason_codes)),
        'runtime_ready_threshold': runtime_ready_threshold,
        'status_rule_summary': (
            f"READY_FOR_RUNTIME when handoff READY and confidence>={runtime_ready_threshold}; "
            "conservative promotion allowed for strong lineage; MONITOR_ONLY remains visible for observability."
        ),
        'prediction_status_summary': (
            f"monitor_only={prediction_status_monitor_only_count} "
            f"ready_for_runtime={prediction_status_ready_for_runtime_count} "
            f"blocked={prediction_status_blocked_count} "
            f"prediction_status_reason_codes={','.join(list(dict.fromkeys(prediction_status_reason_codes))) or 'none'}"
        ),
    }
    prediction_visibility_summary = {
        'prediction_intake_created_count': int(prediction_intake_created_count),
        'prediction_intake_reused_count': int(prediction_intake_reused_count),
        'prediction_candidates_visible_count': int(prediction_candidates_visible_count),
        'prediction_candidates_hidden_count': int(prediction_candidates_hidden_count),
        'prediction_visibility_reason_codes': list(dict.fromkeys(prediction_visibility_reason_codes)),
        'prediction_visibility_summary': (
            f"intake_created={prediction_intake_created_count} intake_reused={prediction_intake_reused_count} "
            f"candidates_visible={prediction_candidates_visible_count} candidates_hidden={prediction_candidates_hidden_count} "
            f"prediction_visibility_reason_codes={','.join(list(dict.fromkeys(prediction_visibility_reason_codes))) or 'none'}"
        ),
    }
    operational_prediction_count = int(prediction_candidates_visible_count)
    handoff_reason_codes = [
        code
        for code in handoff_reason_codes
        if code not in {'CONSENSUS_RAN_NO_PROMOTION', 'PREDICTION_STAGE_EMPTY', 'RISK_STAGE_EMPTY', 'DOWNSTREAM_EVIDENCE_INSUFFICIENT'}
    ]
    if consensus_count > 0 and handoff_count > 0 and operational_prediction_count == 0:
        handoff_reason_codes.append('CONSENSUS_RAN_NO_PROMOTION')
    if handoff_count > 0 and operational_prediction_count == 0:
        handoff_reason_codes.append('PREDICTION_STAGE_EMPTY')
    if operational_prediction_count > 0 and risk_count == 0:
        handoff_reason_codes.append('RISK_STAGE_EMPTY')
    if shortlisted_count > 0 and operational_prediction_count == 0 and risk_count == 0 and paper_execution_count == 0:
        handoff_reason_codes.append('DOWNSTREAM_EVIDENCE_INSUFFICIENT')

    normalized_codes = list(dict.fromkeys(handoff_reason_codes))
    handoff_summary = (
        f"shortlisted_signals={shortlisted_count} handoff_candidates={handoff_count} "
        f"consensus_reviews={consensus_count} prediction_candidates={operational_prediction_count} "
        f"risk_decisions={risk_count} paper_execution_candidates={paper_execution_count} "
        f"handoff_reason_codes={','.join(normalized_codes) or 'none'}"
    )

    return {
        'shortlisted_signals': int(shortlisted_count),
        'handoff_candidates': int(handoff_count),
        'consensus_reviews': int(consensus_count),
        'prediction_candidates': int(operational_prediction_count),
        'risk_decisions': int(risk_count),
        'paper_execution_candidates': int(paper_execution_count),
        'handoff_reason_codes': normalized_codes,
        'stage_source_mismatch': stage_source_mismatch,
        'handoff_summary': handoff_summary,
        'shortlist_handoff_summary': shortlist_handoff_summary,
        'downstream_route_summary': downstream_route_summary,
        'downstream_route_examples': downstream_route_examples,
        'market_link_summary': market_link_summary,
        'market_link_examples': market_link_examples,
        'consensus_alignment': consensus_alignment,
        'handoff_scoring_summary': handoff_scoring_summary,
        'handoff_scoring_examples': handoff_scoring_examples,
        'handoff_borderline_summary': handoff_borderline_summary,
        'handoff_borderline_examples': handoff_borderline_examples,
        'handoff_structural_summary': handoff_structural_summary,
        'handoff_structural_examples': handoff_structural_examples,
        'prediction_intake_summary': prediction_intake_summary,
        'prediction_intake_examples': prediction_intake_examples,
        'prediction_visibility_summary': prediction_visibility_summary,
        'prediction_visibility_examples': prediction_visibility_examples,
        'prediction_artifact_summary': prediction_artifact_summary,
        'prediction_artifact_examples': prediction_artifact_summary.get('prediction_artifact_examples', []),
        'prediction_risk_summary': prediction_risk_summary,
        'prediction_risk_examples': prediction_risk_examples,
        'prediction_risk_caution_summary': prediction_risk_caution_summary,
        'prediction_risk_caution_examples': prediction_risk_caution_examples,
        'prediction_status_summary': prediction_status_summary,
        'prediction_status_examples': prediction_status_examples,
        'paper_execution_summary': paper_execution_summary.get('paper_execution_summary', ''),
        'paper_execution_route_expected': paper_execution_summary.get('paper_execution_route_expected', 0),
        'paper_execution_route_available': paper_execution_summary.get('paper_execution_route_available', 0),
        'paper_execution_route_attempted': paper_execution_summary.get('paper_execution_route_attempted', 0),
        'paper_execution_route_created': paper_execution_summary.get('paper_execution_route_created', 0),
        'paper_execution_route_reused': paper_execution_summary.get('paper_execution_route_reused', 0),
        'paper_execution_route_blocked': paper_execution_summary.get('paper_execution_route_blocked', 0),
        'paper_execution_route_missing_status_count': paper_execution_summary.get('paper_execution_route_missing_status_count', 0),
        'paper_execution_route_reason_codes': paper_execution_summary.get('paper_execution_route_reason_codes', []),
        'paper_execution_examples': paper_execution_summary.get('paper_execution_examples', []),
        'paper_execution_created_count': paper_execution_summary.get('paper_execution_created_count', 0),
        'paper_execution_reused_count': paper_execution_summary.get('paper_execution_reused_count', 0),
        'paper_execution_visible_count': paper_execution_summary.get('paper_execution_visible_count', 0),
        'paper_execution_hidden_count': paper_execution_summary.get('paper_execution_hidden_count', 0),
        'paper_execution_visibility_reason_codes': paper_execution_summary.get('paper_execution_visibility_reason_codes', []),
        'paper_execution_visibility_summary': paper_execution_summary.get('paper_execution_visibility_summary', ''),
        'paper_execution_visibility_examples': paper_execution_summary.get('paper_execution_visibility_examples', []),
        'paper_trade_summary': paper_execution_summary.get('paper_trade_summary', ''),
        'paper_trade_route_expected': paper_execution_summary.get('paper_trade_route_expected', 0),
        'paper_trade_route_available': paper_execution_summary.get('paper_trade_route_available', 0),
        'paper_trade_route_attempted': paper_execution_summary.get('paper_trade_route_attempted', 0),
        'paper_trade_route_created': paper_execution_summary.get('paper_trade_route_created', 0),
        'paper_trade_route_reused': paper_execution_summary.get('paper_trade_route_reused', 0),
        'paper_trade_route_blocked': paper_execution_summary.get('paper_trade_route_blocked', 0),
        'paper_trade_route_reason_codes': paper_execution_summary.get('paper_trade_route_reason_codes', []),
        'paper_trade_decision_created': paper_execution_summary.get('paper_trade_decision_created', 0),
        'paper_trade_decision_reused': paper_execution_summary.get('paper_trade_decision_reused', 0),
        'paper_trade_decision_blocked': paper_execution_summary.get('paper_trade_decision_blocked', 0),
        'paper_trade_decision_dedupe_applied': paper_execution_summary.get('paper_trade_decision_dedupe_applied', 0),
        'paper_trade_decision_reason_codes': paper_execution_summary.get('paper_trade_decision_reason_codes', []),
        'paper_trade_decision_summary': paper_execution_summary.get('paper_trade_decision_summary', ''),
        'paper_trade_decision_examples': paper_execution_summary.get('paper_trade_decision_examples', []),
        'paper_trade_dispatch_created': paper_execution_summary.get('paper_trade_dispatch_created', 0),
        'paper_trade_dispatch_reused': paper_execution_summary.get('paper_trade_dispatch_reused', 0),
        'paper_trade_dispatch_blocked': paper_execution_summary.get('paper_trade_dispatch_blocked', 0),
        'paper_trade_dispatch_dedupe_applied': paper_execution_summary.get('paper_trade_dispatch_dedupe_applied', 0),
        'paper_trade_dispatch_reason_codes': paper_execution_summary.get('paper_trade_dispatch_reason_codes', []),
        'paper_trade_dispatch_summary': paper_execution_summary.get('paper_trade_dispatch_summary', ''),
        'paper_trade_dispatch_examples': paper_execution_summary.get('paper_trade_dispatch_examples', []),
        'final_trade_expected': paper_execution_summary.get('final_trade_expected', 0),
        'final_trade_available': paper_execution_summary.get('final_trade_available', 0),
        'final_trade_attempted': paper_execution_summary.get('final_trade_attempted', 0),
        'final_trade_created': paper_execution_summary.get('final_trade_created', 0),
        'final_trade_reused': paper_execution_summary.get('final_trade_reused', 0),
        'final_trade_blocked': paper_execution_summary.get('final_trade_blocked', 0),
        'final_trade_reason_codes': paper_execution_summary.get('final_trade_reason_codes', []),
        'runtime_rejection_summary': paper_execution_summary.get('runtime_rejection_summary', ''),
        'runtime_rejection_reason_codes': paper_execution_summary.get('runtime_rejection_reason_codes', []),
        'paper_trade_final_summary': paper_execution_summary.get('paper_trade_final_summary', ''),
        'paper_trade_final_examples': paper_execution_summary.get('paper_trade_final_examples', []),
        'paper_trade_examples': paper_execution_summary.get('paper_trade_examples', []),
        'execution_promotion_gate_summary': paper_execution_summary.get('execution_promotion_gate_summary', {}),
        'execution_promotion_gate_examples': paper_execution_summary.get('execution_promotion_gate_examples', []),
        'execution_lineage_summary': paper_execution_summary.get('execution_lineage_summary', {}),
        'final_fanout_summary': paper_execution_summary.get('final_fanout_summary', {}),
        'final_fanout_examples': paper_execution_summary.get('final_fanout_examples', []),
        'cash_pressure_summary': paper_execution_summary.get('cash_pressure_summary', {}),
        'cash_pressure_examples': paper_execution_summary.get('cash_pressure_examples', []),
        'position_exposure_summary': paper_execution_summary.get('position_exposure_summary', {}),
        'execution_readiness_available_count': paper_execution_summary.get('execution_readiness_available_count', 0),
        'execution_readiness_created_count': paper_execution_summary.get('execution_readiness_created_count', 0),
        'execution_readiness_reused_count': paper_execution_summary.get('execution_readiness_reused_count', 0),
        'execution_candidate_visible_count': paper_execution_summary.get('execution_candidate_visible_count', 0),
        'execution_candidate_created_count': paper_execution_summary.get('execution_candidate_created_count', 0),
        'execution_candidate_reused_count': paper_execution_summary.get('execution_candidate_reused_count', 0),
        'execution_candidate_hidden_count': paper_execution_summary.get('execution_candidate_hidden_count', 0),
        'execution_artifact_blocked_count': paper_execution_summary.get('execution_artifact_blocked_count', 0),
        'execution_artifact_reason_codes': paper_execution_summary.get('execution_artifact_reason_codes', []),
        'execution_artifact_summary': paper_execution_summary.get('execution_artifact_summary', ''),
        'execution_artifact_examples': paper_execution_summary.get('execution_artifact_examples', []),
    }


def _infer_stalled_reason_code(*, stalled_stage: str | None, handoff_diagnostics: dict[str, Any]) -> str | None:
    if not stalled_stage:
        return None
    if (
        stalled_stage == 'research'
        and 'SHORTLIST_PRESENT_NO_HANDOFF' in list(handoff_diagnostics.get('handoff_reason_codes') or [])
    ):
        return 'SHORTLIST_PRESENT_NO_HANDOFF'
    return f'{stalled_stage.upper()}_STAGE_EMPTY'


def build_live_paper_autonomy_funnel_snapshot(*, window_minutes: int = 60, preset_name: str | None = None) -> dict[str, Any]:
    safe_window = max(5, min(int(window_minutes or 60), 24 * 60))
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    window_start = timezone.now() - timedelta(minutes=safe_window)

    counts = _collect_funnel_counts(window_start=window_start)
    validation = build_live_paper_validation_digest(preset_name=target_preset)
    heartbeat_summary = build_heartbeat_summary()
    status = _infer_status(counts=counts)
    top_stage = _infer_top_stage(counts=counts)
    stalled_stage = _infer_stalled_stage(counts=counts)
    risk_decision_count = counts.risk_approved_count + counts.risk_blocked_count
    handoff_diagnostics = _build_handoff_diagnostics(window_start=window_start, preset_name=target_preset)
    stalled_reason_code = _infer_stalled_reason_code(stalled_stage=stalled_stage, handoff_diagnostics=handoff_diagnostics)
    if not stalled_reason_code and stalled_stage:
        stage_reason_map = {
            'prediction': 'PREDICTION_STAGE_EMPTY',
            'risk': 'RISK_STAGE_EMPTY',
        }
        reason_candidate = stage_reason_map.get(stalled_stage)
        if reason_candidate and reason_candidate in handoff_diagnostics.get('handoff_reason_codes', []):
            stalled_reason_code = reason_candidate
        elif 'DOWNSTREAM_EVIDENCE_INSUFFICIENT' in handoff_diagnostics.get('handoff_reason_codes', []):
            stalled_reason_code = 'DOWNSTREAM_EVIDENCE_INSUFFICIENT'
    stalled_missing_counter = {
        'scan': 'scan_count',
        'research': 'research_count',
        'prediction': 'prediction_count',
        'risk': 'risk_decision_count',
        'paper_execution': 'paper_execution_count',
    }.get(stalled_stage or '')
    next_action_hint = _infer_hint(status=status, counts=counts, stalled_stage=stalled_stage)

    stages = [
        {
            'stage_name': 'scan',
            'count': counts.scan_count,
            'status': _stage_status(counts.scan_count),
            'summary': f'Scan observed {counts.scan_count} candidate signals in the last {safe_window}m.',
        },
        {
            'stage_name': 'research',
            'count': counts.research_count,
            'status': _stage_status(counts.research_count),
            'summary': f'Research pursued {counts.research_count} handoff candidates.',
        },
        {
            'stage_name': 'prediction',
            'count': counts.prediction_count,
            'status': _stage_status(counts.prediction_count),
            'summary': f'Prediction evaluated {counts.prediction_count} conviction reviews.',
        },
        {
            'stage_name': 'risk',
            'count': counts.risk_approved_count + counts.risk_blocked_count,
            'status': _stage_status(counts.risk_approved_count + counts.risk_blocked_count),
            'summary': f'Risk approved {counts.risk_approved_count} and blocked {counts.risk_blocked_count}.',
        },
        {
            'stage_name': 'paper_execution',
            'count': counts.paper_execution_count,
            'status': _stage_status(counts.paper_execution_count),
            'summary': f'Paper execution registered {counts.paper_execution_count} execution(s).',
        },
    ]

    heartbeat_alive = bool(heartbeat_summary.get('latest_run'))
    funnel_summary = (
        f'{status}: scan={counts.scan_count}, research={counts.research_count}, prediction={counts.prediction_count}, '
        f'risk_approved={counts.risk_approved_count}, risk_blocked={counts.risk_blocked_count}, '
        f'paper_execution={counts.paper_execution_count}, recent_trades={counts.recent_trades_count}, '
        f'heartbeat_alive={heartbeat_alive}, validation={validation.get("validation_status")}, '
        f'handoff={handoff_diagnostics.get("handoff_summary")}.'
    )

    return {
        'window_minutes': safe_window,
        'preset_name': target_preset,
        'funnel_status': status,
        'scan_count': counts.scan_count,
        'research_count': counts.research_count,
        'prediction_count': counts.prediction_count,
        'risk_approved_count': counts.risk_approved_count,
        'risk_blocked_count': counts.risk_blocked_count,
        'risk_decision_count': risk_decision_count,
        'paper_execution_count': counts.paper_execution_count,
        'recent_trades_count': counts.recent_trades_count,
        'top_stage': top_stage,
        'stalled_stage': stalled_stage,
        'stalled_reason_code': stalled_reason_code,
        'stalled_missing_counter': stalled_missing_counter,
        'handoff_reason_codes': handoff_diagnostics.get('handoff_reason_codes', []),
        'stage_source_mismatch': handoff_diagnostics.get('stage_source_mismatch', {}),
        'handoff_summary': handoff_diagnostics.get('handoff_summary', ''),
        'shortlist_handoff_summary': handoff_diagnostics.get('shortlist_handoff_summary', {}),
        'market_link_summary': handoff_diagnostics.get('market_link_summary', {}),
        'market_link_examples': handoff_diagnostics.get('market_link_examples', []),
        'consensus_alignment': handoff_diagnostics.get('consensus_alignment', {}),
        'handoff_scoring_summary': handoff_diagnostics.get('handoff_scoring_summary', {}),
        'handoff_scoring_examples': handoff_diagnostics.get('handoff_scoring_examples', []),
        'handoff_borderline_summary': handoff_diagnostics.get('handoff_borderline_summary', {}),
        'handoff_borderline_examples': handoff_diagnostics.get('handoff_borderline_examples', []),
        'prediction_intake_summary': handoff_diagnostics.get('prediction_intake_summary', {}),
        'prediction_intake_examples': handoff_diagnostics.get('prediction_intake_examples', []),
        'prediction_visibility_summary': handoff_diagnostics.get('prediction_visibility_summary', {}),
        'prediction_visibility_examples': handoff_diagnostics.get('prediction_visibility_examples', []),
        'prediction_artifact_summary': handoff_diagnostics.get('prediction_artifact_summary', {}),
        'prediction_artifact_examples': handoff_diagnostics.get('prediction_artifact_examples', []),
        'prediction_risk_summary': handoff_diagnostics.get('prediction_risk_summary', {}),
        'prediction_risk_examples': handoff_diagnostics.get('prediction_risk_examples', []),
        'prediction_risk_caution_summary': handoff_diagnostics.get('prediction_risk_caution_summary', {}),
        'prediction_risk_caution_examples': handoff_diagnostics.get('prediction_risk_caution_examples', []),
        'prediction_status_summary': handoff_diagnostics.get('prediction_status_summary', {}),
        'prediction_status_examples': handoff_diagnostics.get('prediction_status_examples', []),
        'paper_execution_summary': handoff_diagnostics.get('paper_execution_summary', ''),
        'paper_execution_route_expected': handoff_diagnostics.get('paper_execution_route_expected', 0),
        'paper_execution_route_available': handoff_diagnostics.get('paper_execution_route_available', 0),
        'paper_execution_route_attempted': handoff_diagnostics.get('paper_execution_route_attempted', 0),
        'paper_execution_route_created': handoff_diagnostics.get('paper_execution_route_created', 0),
        'paper_execution_route_reused': handoff_diagnostics.get('paper_execution_route_reused', 0),
        'paper_execution_route_blocked': handoff_diagnostics.get('paper_execution_route_blocked', 0),
        'paper_execution_route_missing_status_count': handoff_diagnostics.get('paper_execution_route_missing_status_count', 0),
        'paper_execution_route_reason_codes': handoff_diagnostics.get('paper_execution_route_reason_codes', []),
        'paper_execution_examples': handoff_diagnostics.get('paper_execution_examples', []),
        'paper_execution_created_count': handoff_diagnostics.get('paper_execution_created_count', 0),
        'paper_execution_reused_count': handoff_diagnostics.get('paper_execution_reused_count', 0),
        'paper_execution_visible_count': handoff_diagnostics.get('paper_execution_visible_count', 0),
        'paper_execution_hidden_count': handoff_diagnostics.get('paper_execution_hidden_count', 0),
        'paper_execution_visibility_reason_codes': handoff_diagnostics.get('paper_execution_visibility_reason_codes', []),
        'paper_execution_visibility_summary': handoff_diagnostics.get('paper_execution_visibility_summary', ''),
        'paper_execution_visibility_examples': handoff_diagnostics.get('paper_execution_visibility_examples', []),
        'paper_trade_summary': handoff_diagnostics.get('paper_trade_summary', ''),
        'paper_trade_route_expected': handoff_diagnostics.get('paper_trade_route_expected', 0),
        'paper_trade_route_available': handoff_diagnostics.get('paper_trade_route_available', 0),
        'paper_trade_route_attempted': handoff_diagnostics.get('paper_trade_route_attempted', 0),
        'paper_trade_route_created': handoff_diagnostics.get('paper_trade_route_created', 0),
        'paper_trade_route_reused': handoff_diagnostics.get('paper_trade_route_reused', 0),
        'paper_trade_route_blocked': handoff_diagnostics.get('paper_trade_route_blocked', 0),
        'paper_trade_route_reason_codes': handoff_diagnostics.get('paper_trade_route_reason_codes', []),
        'paper_trade_decision_created': handoff_diagnostics.get('paper_trade_decision_created', 0),
        'paper_trade_decision_reused': handoff_diagnostics.get('paper_trade_decision_reused', 0),
        'paper_trade_decision_blocked': handoff_diagnostics.get('paper_trade_decision_blocked', 0),
        'paper_trade_decision_dedupe_applied': handoff_diagnostics.get('paper_trade_decision_dedupe_applied', 0),
        'paper_trade_decision_reason_codes': handoff_diagnostics.get('paper_trade_decision_reason_codes', []),
        'paper_trade_decision_summary': handoff_diagnostics.get('paper_trade_decision_summary', ''),
        'paper_trade_decision_examples': handoff_diagnostics.get('paper_trade_decision_examples', []),
        'paper_trade_dispatch_created': handoff_diagnostics.get('paper_trade_dispatch_created', 0),
        'paper_trade_dispatch_reused': handoff_diagnostics.get('paper_trade_dispatch_reused', 0),
        'paper_trade_dispatch_blocked': handoff_diagnostics.get('paper_trade_dispatch_blocked', 0),
        'paper_trade_dispatch_dedupe_applied': handoff_diagnostics.get('paper_trade_dispatch_dedupe_applied', 0),
        'paper_trade_dispatch_reason_codes': handoff_diagnostics.get('paper_trade_dispatch_reason_codes', []),
        'paper_trade_dispatch_summary': handoff_diagnostics.get('paper_trade_dispatch_summary', ''),
        'paper_trade_dispatch_examples': handoff_diagnostics.get('paper_trade_dispatch_examples', []),
        'final_trade_expected': handoff_diagnostics.get('final_trade_expected', 0),
        'final_trade_available': handoff_diagnostics.get('final_trade_available', 0),
        'final_trade_attempted': handoff_diagnostics.get('final_trade_attempted', 0),
        'final_trade_created': handoff_diagnostics.get('final_trade_created', 0),
        'final_trade_reused': handoff_diagnostics.get('final_trade_reused', 0),
        'final_trade_blocked': handoff_diagnostics.get('final_trade_blocked', 0),
        'final_trade_reason_codes': handoff_diagnostics.get('final_trade_reason_codes', []),
        'runtime_rejection_summary': handoff_diagnostics.get('runtime_rejection_summary', ''),
        'runtime_rejection_reason_codes': handoff_diagnostics.get('runtime_rejection_reason_codes', []),
        'paper_trade_final_summary': handoff_diagnostics.get('paper_trade_final_summary', ''),
        'paper_trade_final_examples': handoff_diagnostics.get('paper_trade_final_examples', []),
        'paper_trade_examples': handoff_diagnostics.get('paper_trade_examples', []),
        'execution_lineage_summary': handoff_diagnostics.get('execution_lineage_summary', {}),
        'execution_promotion_gate_summary': handoff_diagnostics.get('execution_promotion_gate_summary', {}),
        'execution_promotion_gate_examples': handoff_diagnostics.get('execution_promotion_gate_examples', []),
        'final_fanout_summary': handoff_diagnostics.get('final_fanout_summary', {}),
        'final_fanout_examples': handoff_diagnostics.get('final_fanout_examples', []),
        'cash_pressure_summary': handoff_diagnostics.get('cash_pressure_summary', {}),
        'cash_pressure_examples': handoff_diagnostics.get('cash_pressure_examples', []),
        'position_exposure_summary': handoff_diagnostics.get('position_exposure_summary', {}),
        'execution_readiness_available_count': handoff_diagnostics.get('execution_readiness_available_count', 0),
        'execution_readiness_created_count': handoff_diagnostics.get('execution_readiness_created_count', 0),
        'execution_readiness_reused_count': handoff_diagnostics.get('execution_readiness_reused_count', 0),
        'execution_candidate_visible_count': handoff_diagnostics.get('execution_candidate_visible_count', 0),
        'execution_candidate_created_count': handoff_diagnostics.get('execution_candidate_created_count', 0),
        'execution_candidate_reused_count': handoff_diagnostics.get('execution_candidate_reused_count', 0),
        'execution_candidate_hidden_count': handoff_diagnostics.get('execution_candidate_hidden_count', 0),
        'execution_artifact_blocked_count': handoff_diagnostics.get('execution_artifact_blocked_count', 0),
        'execution_artifact_reason_codes': handoff_diagnostics.get('execution_artifact_reason_codes', []),
        'execution_artifact_summary': handoff_diagnostics.get('execution_artifact_summary', ''),
        'execution_artifact_examples': handoff_diagnostics.get('execution_artifact_examples', []),
        'shortlisted_signals': handoff_diagnostics.get('shortlisted_signals', 0),
        'handoff_candidates': handoff_diagnostics.get('handoff_candidates', 0),
        'consensus_reviews': handoff_diagnostics.get('consensus_reviews', 0),
        'prediction_candidates': handoff_diagnostics.get('prediction_candidates', 0),
        'risk_decisions': handoff_diagnostics.get('risk_decisions', 0),
        'paper_execution_candidates': handoff_diagnostics.get('paper_execution_candidates', 0),
        'next_action_hint': next_action_hint,
        'funnel_summary': funnel_summary,
        'stages': stages,
    }
