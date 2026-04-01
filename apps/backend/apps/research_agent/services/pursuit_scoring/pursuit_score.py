from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import (
    NarrativeDivergenceState,
    ResearchHandoffStatus,
    ResearchPriorityBucket,
    ResearchPursuitPriorityBucket,
    ResearchPursuitScoreStatus,
    ResearchStructuralStatus,
)


def _as_component(value: Decimal) -> Decimal:
    return max(Decimal('0.0000'), min(Decimal('1.0000'), value)).quantize(Decimal('0.0001'))


def _from_priority_bucket(bucket: str | None) -> Decimal:
    mapping = {
        ResearchPriorityBucket.CRITICAL: Decimal('1.0000'),
        ResearchPriorityBucket.HIGH: Decimal('0.8200'),
        ResearchPriorityBucket.MEDIUM: Decimal('0.6200'),
        ResearchPriorityBucket.LOW: Decimal('0.3800'),
        ResearchPriorityBucket.IGNORE: Decimal('0.0800'),
    }
    return mapping.get(bucket, Decimal('0.2500'))


def _from_divergence(divergence_record) -> Decimal:
    if not divergence_record:
        return Decimal('0.2000')
    base = Decimal(str(divergence_record.divergence_score or 0))
    if divergence_record.divergence_state == NarrativeDivergenceState.HIGH_DIVERGENCE:
        return _as_component(base + Decimal('0.2200'))
    if divergence_record.divergence_state == NarrativeDivergenceState.MODEST_DIVERGENCE:
        return _as_component(base + Decimal('0.1200'))
    return _as_component(base)


def compute_pursuit_score(*, assessment, handoff_priority):
    components = {
        'narrative_priority': _from_priority_bucket(getattr(handoff_priority, 'priority_bucket', None)),
        'divergence_strength': _from_divergence(getattr(handoff_priority, 'linked_divergence_record', None)),
        'liquidity_quality': Decimal('1.0000') if assessment.liquidity_state == 'strong' else Decimal('0.7000') if assessment.liquidity_state == 'adequate' else Decimal('0.4200') if assessment.liquidity_state == 'weak' else Decimal('0.1000'),
        'volume_quality': Decimal('1.0000') if assessment.volume_state == 'strong' else Decimal('0.7000') if assessment.volume_state == 'adequate' else Decimal('0.4200') if assessment.volume_state == 'weak' else Decimal('0.1000'),
        'time_window_quality': Decimal('1.0000') if assessment.time_to_resolution_state == 'good_window' else Decimal('0.6000') if assessment.time_to_resolution_state == 'short_window' else Decimal('0.2200'),
        'activity_quality': Decimal('1.0000') if assessment.market_activity_state == 'active' else Decimal('0.7000') if assessment.market_activity_state == 'moderate' else Decimal('0.2500') if assessment.market_activity_state == 'stale' else Decimal('0.0000'),
    }

    weighted_score = (
        components['narrative_priority'] * Decimal('0.22')
        + components['divergence_strength'] * Decimal('0.16')
        + components['liquidity_quality'] * Decimal('0.18')
        + components['volume_quality'] * Decimal('0.14')
        + components['time_window_quality'] * Decimal('0.16')
        + components['activity_quality'] * Decimal('0.14')
    ).quantize(Decimal('0.0001'))

    if assessment.structural_status == ResearchStructuralStatus.BLOCKED:
        status = ResearchPursuitScoreStatus.BLOCK
    elif assessment.structural_status == ResearchStructuralStatus.DEFERRED:
        status = ResearchPursuitScoreStatus.DEFER
    elif (
        assessment.structural_status == ResearchStructuralStatus.PREDICTION_READY
        and weighted_score >= Decimal('0.6200')
        and getattr(handoff_priority, 'handoff_status', '') != ResearchHandoffStatus.BLOCKED
    ):
        status = ResearchPursuitScoreStatus.READY_FOR_PREDICTION
    elif weighted_score >= Decimal('0.7600') and getattr(handoff_priority, 'handoff_status', '') != ResearchHandoffStatus.BLOCKED:
        status = ResearchPursuitScoreStatus.READY_FOR_PREDICTION
    elif weighted_score >= Decimal('0.4200'):
        status = ResearchPursuitScoreStatus.KEEP_ON_RESEARCH_WATCHLIST
    else:
        status = ResearchPursuitScoreStatus.DEFER

    if status == ResearchPursuitScoreStatus.BLOCK:
        bucket = ResearchPursuitPriorityBucket.IGNORE
    elif weighted_score >= Decimal('0.8600'):
        bucket = ResearchPursuitPriorityBucket.CRITICAL
    elif weighted_score >= Decimal('0.7200'):
        bucket = ResearchPursuitPriorityBucket.HIGH
    elif weighted_score >= Decimal('0.5200'):
        bucket = ResearchPursuitPriorityBucket.MEDIUM
    elif weighted_score >= Decimal('0.3000'):
        bucket = ResearchPursuitPriorityBucket.LOW
    else:
        bucket = ResearchPursuitPriorityBucket.IGNORE

    summary = f'score={weighted_score} bucket={bucket} status={status}'
    serializable = {key: str(value.quantize(Decimal('0.0001'))) for key, value in components.items()}
    return weighted_score, bucket, status, serializable, summary
