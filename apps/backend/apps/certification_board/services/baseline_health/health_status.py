from __future__ import annotations

from decimal import Decimal

from apps.certification_board.models import (
    BaselineHealthReadinessStatus,
    BaselineHealthSignalDirection,
    BaselineHealthSignalSeverity,
    BaselineHealthSignalType,
    BaselineHealthStatusCode,
)


def _clamp(value: Decimal) -> Decimal:
    if value < Decimal('0'):
        return Decimal('0')
    if value > Decimal('1'):
        return Decimal('1')
    return value


def derive_health_status(*, candidate, consolidated: dict) -> dict:
    calibration_error = Decimal(consolidated.get('calibration_error') or 0)
    risk_precision = Decimal(consolidated.get('risk_precision') or 0)
    opportunity_quality = Decimal(consolidated.get('opportunity_quality') or 0)
    drift_indicator = Decimal(consolidated.get('drift_indicator') or 0)
    provider_bias = Decimal(consolidated.get('provider_bias') or 0)
    category_bias = Decimal(consolidated.get('category_bias') or 0)
    watch_ratio = Decimal(consolidated.get('watch_ratio') or 0)
    risk_block_rate = Decimal(consolidated.get('risk_block_rate') or 0)

    calibration_health = _clamp(Decimal('1') - calibration_error)
    risk_health = _clamp(Decimal('1') - risk_block_rate + (risk_precision * Decimal('0.4')))
    opportunity_health = _clamp(opportunity_quality)
    drift_risk = _clamp(drift_indicator + (provider_bias * Decimal('0.2')) + (category_bias * Decimal('0.2')))
    regression_risk = _clamp((Decimal('1') - risk_precision) * Decimal('0.4') + watch_ratio * Decimal('0.3') + risk_block_rate * Decimal('0.3'))

    reason_codes: list[str] = []
    blockers = list(candidate.blockers or [])
    signals: list[dict] = []

    if candidate.readiness_status == BaselineHealthReadinessStatus.NEEDS_MORE_DATA:
        reason_codes.append('NEEDS_MORE_DATA')
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.INSUFFICIENT_OBSERVATION,
                'signal_severity': BaselineHealthSignalSeverity.MEDIUM,
                'signal_direction': BaselineHealthSignalDirection.STABLE,
                'rationale': 'Baseline has insufficient recent observations for confident health classification.',
                'evidence_summary': {
                    'opportunity_sample_count': consolidated.get('opportunity_sample_count', 0),
                    'risk_sample_count': consolidated.get('risk_sample_count', 0),
                },
            }
        )

    if calibration_error > Decimal('0.15'):
        reason_codes.append('CALIBRATION_DRIFT')
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.CALIBRATION_DRIFT,
                'signal_severity': BaselineHealthSignalSeverity.HIGH,
                'signal_direction': BaselineHealthSignalDirection.DEGRADING,
                'rationale': 'Calibration error moved above conservative threshold.',
                'evidence_summary': {'calibration_error': str(calibration_error)},
            }
        )

    if risk_precision < Decimal('0.52') or risk_block_rate > Decimal('0.45'):
        reason_codes.append('RISK_PRECISION_DROP')
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.RISK_PRECISION_DROP,
                'signal_severity': BaselineHealthSignalSeverity.HIGH,
                'signal_direction': BaselineHealthSignalDirection.DEGRADING,
                'rationale': 'Risk gate precision or risk blocking profile suggests degradation.',
                'evidence_summary': {'risk_precision': str(risk_precision), 'risk_block_rate': str(risk_block_rate)},
            }
        )

    if opportunity_quality < Decimal('0.42'):
        reason_codes.append('OPPORTUNITY_CONVICTION_DROP')
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.OPPORTUNITY_CONVICTION_DROP,
                'signal_severity': BaselineHealthSignalSeverity.MEDIUM,
                'signal_direction': BaselineHealthSignalDirection.DEGRADING,
                'rationale': 'Opportunity conviction quality is trending below healthy levels.',
                'evidence_summary': {'opportunity_quality': str(opportunity_quality)},
            }
        )

    if provider_bias > Decimal('0.60'):
        reason_codes.append('PROVIDER_BIAS_REAPPEARANCE')
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.PROVIDER_BIAS_REAPPEARANCE,
                'signal_severity': BaselineHealthSignalSeverity.HIGH,
                'signal_direction': BaselineHealthSignalDirection.DEGRADING,
                'rationale': 'Provider bias indicator reappeared above acceptable tolerance.',
                'evidence_summary': {'provider_bias': str(provider_bias)},
            }
        )

    if category_bias > Decimal('0.60'):
        reason_codes.append('CATEGORY_BIAS_REAPPEARANCE')
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.CATEGORY_BIAS_REAPPEARANCE,
                'signal_severity': BaselineHealthSignalSeverity.HIGH,
                'signal_direction': BaselineHealthSignalDirection.DEGRADING,
                'rationale': 'Category bias indicator reappeared above acceptable tolerance.',
                'evidence_summary': {'category_bias': str(category_bias)},
            }
        )

    if watch_ratio > Decimal('0.45'):
        reason_codes.append('WATCHLIST_NOISE_INCREASE')
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.WATCHLIST_NOISE_INCREASE,
                'signal_severity': BaselineHealthSignalSeverity.MEDIUM,
                'signal_direction': BaselineHealthSignalDirection.DEGRADING,
                'rationale': 'Watch-required ratio is elevated and can signal unstable gating quality.',
                'evidence_summary': {'watch_ratio': str(watch_ratio)},
            }
        )

    critical_count = sum(1 for s in signals if s['signal_severity'] in {BaselineHealthSignalSeverity.HIGH, BaselineHealthSignalSeverity.CRITICAL})

    if candidate.readiness_status == BaselineHealthReadinessStatus.BLOCKED:
        status_code = BaselineHealthStatusCode.REVIEW_REQUIRED
        reason_codes.append('BLOCKED_CANDIDATE')
        blockers.append('candidate_blocked_for_health_assessment')
    elif candidate.readiness_status == BaselineHealthReadinessStatus.NEEDS_MORE_DATA and critical_count == 0:
        status_code = BaselineHealthStatusCode.INSUFFICIENT_DATA
    elif critical_count >= 3:
        status_code = BaselineHealthStatusCode.ROLLBACK_REVIEW_RECOMMENDED
        signals.append(
            {
                'signal_type': BaselineHealthSignalType.ROLLBACK_PRESSURE,
                'signal_severity': BaselineHealthSignalSeverity.CRITICAL,
                'signal_direction': BaselineHealthSignalDirection.DEGRADING,
                'rationale': 'Multiple severe degradation signals coincide and raise rollback review pressure.',
                'evidence_summary': {'high_or_critical_signal_count': critical_count},
            }
        )
        reason_codes.append('ROLLBACK_PRESSURE')
    elif critical_count >= 2 or drift_risk > Decimal('0.65'):
        status_code = BaselineHealthStatusCode.REVIEW_REQUIRED
    elif critical_count == 1 or regression_risk > Decimal('0.55') or candidate.target_scope == 'global':
        status_code = BaselineHealthStatusCode.UNDER_WATCH
    elif calibration_health > Decimal('0.75') and risk_health > Decimal('0.70') and opportunity_health > Decimal('0.45'):
        status_code = BaselineHealthStatusCode.HEALTHY
    else:
        status_code = BaselineHealthStatusCode.DEGRADED

    rationale = f'Health classification derived from conservative rules for {candidate.target_component}/{candidate.target_scope}.'

    return {
        'health_status': status_code,
        'calibration_health_score': calibration_health,
        'risk_gate_health_score': risk_health,
        'opportunity_quality_health_score': opportunity_health,
        'drift_risk_score': drift_risk,
        'regression_risk_score': regression_risk,
        'rationale': rationale,
        'reason_codes': sorted(set(reason_codes)),
        'blockers': sorted(set(blockers)),
        'signals': signals,
        'metadata': {'consolidated_signals': consolidated},
    }
