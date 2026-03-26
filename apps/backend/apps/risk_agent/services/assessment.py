from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from apps.learning_memory.models import LearningAdjustment
from apps.markets.models import Market
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueStatus
from apps.paper_trading.models import PaperPositionStatus
from apps.paper_trading.services.portfolio import get_active_account
from apps.prediction_agent.models import PredictionScore
from apps.proposal_engine.models import TradeProposal
from apps.real_data_sync.models import ProviderSyncRun
from apps.risk_agent.models import RiskAssessment, RiskAssessmentStatus, RiskLevel
from apps.runtime_governor.services.state import get_runtime_state
from apps.safety_guard.services.evaluation import get_safety_status

ZERO = Decimal('0')


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _latest_prediction(market: Market | None) -> PredictionScore | None:
    if market is None:
        return None
    return PredictionScore.objects.filter(market=market).order_by('-created_at', '-id').first()


def _provider_stale_penalty(market: Market | None) -> tuple[Decimal, dict]:
    if market is None:
        return Decimal('8.00'), {'reason': 'market_missing'}
    latest_sync = ProviderSyncRun.objects.filter(provider=market.provider.slug).order_by('-started_at', '-id').first()
    if latest_sync is None or latest_sync.status != 'SUCCESS':
        return Decimal('14.00'), {'reason': 'provider_sync_missing_or_failed'}
    age_minutes = int((market.updated_at - latest_sync.finished_at).total_seconds() / 60) if latest_sync.finished_at else 999
    if age_minutes > 180:
        return Decimal('10.00'), {'reason': 'provider_sync_stale', 'age_minutes': age_minutes}
    return Decimal('1.50'), {'reason': 'provider_sync_recent', 'age_minutes': age_minutes}


def run_risk_assessment(*, market: Market | None = None, proposal: TradeProposal | None = None, prediction_score: PredictionScore | None = None, metadata: dict | None = None) -> RiskAssessment:
    metadata = metadata or {}
    if market is None and proposal is not None:
        market = proposal.market
    if prediction_score is None:
        prediction_score = _latest_prediction(market)

    account = get_active_account()
    open_positions = account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0)
    same_market_exposure = ZERO
    total_open_exposure = ZERO
    if market is not None:
        same_market_exposure = sum((position.market_value for position in open_positions.filter(market=market)), ZERO)
    total_open_exposure = sum((position.market_value for position in open_positions), ZERO)

    liquidity_penalty = Decimal('0.00')
    momentum_penalty = Decimal('4.00')
    confidence_penalty = Decimal('8.00')
    provider_penalty, provider_context = _provider_stale_penalty(market)
    runtime_penalty = Decimal('0.00')

    factors: list[dict] = []

    if market is None:
        liquidity_penalty += Decimal('15.00')
        factors.append({'factor': 'missing_market', 'penalty': '15.00', 'detail': 'Assessment degraded because market context is missing.'})
    else:
        if Decimal(str(market.liquidity or 0)) < Decimal('15000'):
            liquidity_penalty += Decimal('10.00')
            factors.append({'factor': 'low_liquidity', 'penalty': '10.00', 'detail': f'Market liquidity={market.liquidity} is below conservative threshold.'})
        if Decimal(str(market.volume_24h or 0)) < Decimal('1000'):
            liquidity_penalty += Decimal('6.00')
            factors.append({'factor': 'low_volume', 'penalty': '6.00', 'detail': f'24h volume={market.volume_24h} is thin.'})

    if prediction_score is not None:
        confidence = Decimal(str(prediction_score.confidence))
        edge = Decimal(str(prediction_score.edge))
        if confidence < Decimal('0.45'):
            confidence_penalty += Decimal('14.00')
            factors.append({'factor': 'low_prediction_confidence', 'penalty': '14.00', 'detail': f'Prediction confidence={confidence}.'})
        if edge <= Decimal('0.00'):
            momentum_penalty += Decimal('12.00')
            factors.append({'factor': 'negative_or_zero_edge', 'penalty': '12.00', 'detail': f'Prediction edge={edge}.'})
    else:
        confidence_penalty += Decimal('12.00')
        factors.append({'factor': 'missing_prediction', 'penalty': '12.00', 'detail': 'Run prediction first for stronger risk context.'})

    if same_market_exposure >= Decimal('500.00'):
        factors.append({'factor': 'same_market_exposure_pressure', 'penalty': '12.00', 'detail': f'Current same-market exposure={same_market_exposure}.'})
    if total_open_exposure >= Decimal('2800.00'):
        factors.append({'factor': 'portfolio_exposure_pressure', 'penalty': '10.00', 'detail': f'Total open exposure={total_open_exposure}.'})

    runtime_state = get_runtime_state()
    mode_penalty = {'OBSERVE_ONLY': Decimal('10.00'), 'PAPER_ASSIST': Decimal('6.00'), 'PAPER_SEMI_AUTO': Decimal('3.00'), 'PAPER_AUTO': Decimal('0.00')}
    runtime_penalty += mode_penalty.get(runtime_state.current_mode, Decimal('4.00'))
    factors.append({'factor': 'runtime_mode', 'penalty': str(runtime_penalty), 'detail': f'Runtime mode={runtime_state.current_mode}.'})

    safety = get_safety_status()
    safety_status = safety.get('status', 'HEALTHY')
    safety_pressure_map = {'HEALTHY': Decimal('0.00'), 'WARNING': Decimal('8.00'), 'COOLDOWN': Decimal('15.00'), 'PAUSED': Decimal('25.00'), 'HARD_STOP': Decimal('40.00'), 'KILL_SWITCH': Decimal('50.00')}
    safety_penalty = safety_pressure_map.get(safety_status, Decimal('0.00'))
    if safety_penalty > ZERO:
        factors.append({'factor': 'safety_pressure', 'penalty': str(safety_penalty), 'detail': f'Safety status={safety_status}.'})

    learning_penalty = Decimal('0.00')
    active_penalties = LearningAdjustment.objects.filter(is_active=True, magnitude__lt=ZERO).count()
    if active_penalties:
        learning_penalty = min(Decimal(active_penalties) * Decimal('1.50'), Decimal('8.00'))
        factors.append({'factor': 'learning_penalties', 'penalty': str(learning_penalty), 'detail': f'Active negative learning adjustments={active_penalties}.'})

    queue_pressure = OperatorQueueItem.objects.filter(status=OperatorQueueStatus.PENDING, priority__in=[OperatorQueuePriority.HIGH, OperatorQueuePriority.CRITICAL]).count()
    queue_penalty = Decimal('0.00')
    if queue_pressure >= 3:
        queue_penalty = Decimal('5.00')
        factors.append({'factor': 'operator_queue_pressure', 'penalty': '5.00', 'detail': f'High-priority pending queue items={queue_pressure}.'})

    provider_note = {'factor': 'provider_freshness', 'penalty': str(provider_penalty), **provider_context}
    factors.append(provider_note)

    penalties = liquidity_penalty + momentum_penalty + confidence_penalty + provider_penalty + runtime_penalty + safety_penalty + learning_penalty + queue_penalty

    penalties += Decimal('12.00') if same_market_exposure >= Decimal('500.00') else ZERO
    penalties += Decimal('10.00') if total_open_exposure >= Decimal('2800.00') else ZERO

    risk_score = _q2(max(ZERO, Decimal('100.00') - penalties))

    blocked_conditions = [
        safety_status in {'HARD_STOP', 'KILL_SWITCH', 'PAUSED'},
        market is not None and not market.is_active,
    ]
    if any(blocked_conditions):
        risk_level = RiskLevel.BLOCKED
    elif risk_score >= Decimal('72.00'):
        risk_level = RiskLevel.LOW
    elif risk_score >= Decimal('46.00'):
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.HIGH

    summary = (
        f'Risk agent assessment level={risk_level}. score={risk_score}. '
        f'Key pressure: safety={safety_status}, runtime={runtime_state.current_mode}, '
        f'portfolio_exposure={total_open_exposure}.'
    )

    return RiskAssessment.objects.create(
        market=market,
        proposal=proposal,
        prediction_score=prediction_score,
        assessment_status=RiskAssessmentStatus.SUCCESS,
        risk_level=risk_level,
        risk_score=risk_score,
        key_risk_factors=factors,
        narrative_risk_summary=summary,
        liquidity_risk=_q2(liquidity_penalty),
        volatility_or_momentum_risk=_q2(momentum_penalty),
        confidence_risk=_q2(confidence_penalty),
        provider_risk=_q2(provider_penalty),
        runtime_risk=_q2(runtime_penalty),
        safety_context={
            'status': safety_status,
            'cooldown_until_cycle': safety.get('cooldown_until_cycle'),
            'kill_switch_enabled': safety.get('kill_switch_enabled'),
            'hard_stop_active': safety.get('hard_stop_active'),
        },
        metadata={
            **metadata,
            'paper_demo_only': True,
            'same_market_exposure': str(same_market_exposure),
            'total_open_exposure': str(total_open_exposure),
            'operator_queue_high_pressure': queue_pressure,
            'runtime_mode': runtime_state.current_mode,
            'reference_price': str(market.current_yes_price if market and market.current_yes_price else Decimal('1.0')),
        },
    )
