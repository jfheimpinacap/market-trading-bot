from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import re
from typing import Any

from django.db.models import Sum
from django.conf import settings
from django.utils import timezone

from apps.autonomous_trader.models import AutonomousTradeCycleRun
from apps.markets.models import Market
from apps.mission_control.services.live_paper_bootstrap import PRESET_NAME
from apps.mission_control.services.live_paper_validation import build_live_paper_validation_digest
from apps.mission_control.services.session_heartbeat import build_heartbeat_summary
from apps.paper_trading.models import PaperTrade, PaperTradeStatus
from apps.paper_trading.services.portfolio import build_account_summary, get_active_account
from apps.prediction_agent.models import PredictionConvictionReview, PredictionIntakeCandidate, PredictionIntakeRun
from apps.prediction_agent.services.run import run_prediction_intake_review
from apps.research_agent.models import NarrativeConsensusRecord
from apps.research_agent.models import MarketUniverseScanRun, NarrativeSignal, NarrativeSignalStatus, PredictionHandoffCandidate
from apps.research_agent.models import PredictionHandoffStatus, ResearchHandoffPriority, ResearchHandoffStatus, ResearchPursuitRun, ResearchStructuralAssessment
from apps.risk_agent.models import RiskApprovalDecision

FUNNEL_ACTIVE = 'ACTIVE'
FUNNEL_THIN_FLOW = 'THIN_FLOW'
FUNNEL_STALLED = 'STALLED'

STAGE_ACTIVE = 'ACTIVE'
STAGE_LOW = 'LOW'
STAGE_EMPTY = 'EMPTY'

_LOW_THRESHOLD = 3
_MARKET_LINK_CONFIDENCE_THRESHOLD = Decimal('1.00')
_PREDICTION_INTAKE_CONFIDENCE_THRESHOLD = Decimal('0.5500')
_HANDOFF_SCORING_EXAMPLES_LIMIT = 3
_TOKEN_STOPWORDS = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'will', 'over'}
_DOWNSTREAM_ROUTE_NAME = 'research_pursuit_review'
_PREDICTION_INTAKE_ROUTE_NAME = 'prediction_intake_review'


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


def _build_handoff_diagnostics(*, window_start) -> dict[str, Any]:
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
    paper_qs = AutonomousTradeCycleRun.objects.filter(started_at__gte=window_start)

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
    paper_execution_count = paper_qs.count()

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
    existing_intake_handoff_ids = {
        int(handoff_id)
        for handoff_id in PredictionIntakeCandidate.objects.filter(
            linked_prediction_handoff_candidate_id__in=list(eligible_handoff_ids)
        ).values_list('linked_prediction_handoff_candidate_id', flat=True)
        if handoff_id is not None
    }
    bridge_attempted = False
    bridge_created_handoff_ids: set[int] = set()
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

    if shortlisted_count > 0 and handoff_count == 0:
        handoff_reason_codes.append('SHORTLIST_PRESENT_NO_HANDOFF')
    if route_missing_count > 0:
        handoff_reason_codes.append('DOWNSTREAM_ROUTE_MISSING')
    if handoff_count > 0:
        handoff_reason_codes.append('HANDOFF_CREATED')
    if handoff_count > 0 and consensus_count == 0:
        handoff_reason_codes.append('CONSENSUS_NOT_RUN')
    if consensus_count > 0 and handoff_count > 0 and prediction_count == 0:
        handoff_reason_codes.append('CONSENSUS_RAN_NO_PROMOTION')
    if handoff_count > 0 and prediction_count == 0:
        handoff_reason_codes.append('PREDICTION_STAGE_EMPTY')
    if prediction_count > 0 and risk_count == 0:
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

    if shortlisted_count > 0 and prediction_count == 0 and risk_count == 0 and paper_execution_count == 0:
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

    normalized_codes = list(dict.fromkeys(handoff_reason_codes))
    handoff_summary = (
        f"shortlisted_signals={shortlisted_count} handoff_candidates={handoff_count} "
        f"consensus_reviews={consensus_count} prediction_candidates={prediction_count} "
        f"risk_decisions={risk_count} paper_execution_candidates={paper_execution_count} "
        f"handoff_reason_codes={','.join(normalized_codes) or 'none'}"
    )

    return {
        'shortlisted_signals': int(shortlisted_count),
        'handoff_candidates': int(handoff_count),
        'consensus_reviews': int(consensus_count),
        'prediction_candidates': int(prediction_count),
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
        'prediction_intake_summary': prediction_intake_summary,
        'prediction_intake_examples': prediction_intake_examples,
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
    handoff_diagnostics = _build_handoff_diagnostics(window_start=window_start)
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
        'prediction_intake_summary': handoff_diagnostics.get('prediction_intake_summary', {}),
        'prediction_intake_examples': handoff_diagnostics.get('prediction_intake_examples', []),
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
