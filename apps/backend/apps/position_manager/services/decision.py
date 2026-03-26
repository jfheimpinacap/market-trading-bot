from __future__ import annotations

from decimal import Decimal

from apps.position_manager.models import PositionLifecycleStatus


def decide_lifecycle_action(snapshot: dict) -> tuple[str, list[str], str, Decimal]:
    prediction_drift = Decimal(snapshot.get('prediction_drift', '0'))
    edge = Decimal(snapshot.get('current_edge_estimate', '0'))
    confidence = Decimal(snapshot.get('confidence', '0.5'))
    unrealized_pnl = Decimal(snapshot.get('pnl_unrealized', '0'))
    narrative_drift = Decimal(snapshot.get('narrative_drift', '0'))

    reasons: list[str] = []

    if snapshot.get('runtime_mode') == 'OBSERVE_ONLY':
        reasons.append('runtime_observe_only')
        return PositionLifecycleStatus.REVIEW_REQUIRED, reasons, 'Runtime mode requires manual review for any active governance action.', Decimal('0.88')

    if snapshot.get('safety_state') in {'HARD_STOP', 'PAUSED'}:
        reasons.append('safety_pressure')
        return PositionLifecycleStatus.REVIEW_REQUIRED, reasons, 'Safety guard status requires operator review before lifecycle action.', Decimal('0.90')

    if snapshot.get('watch_severity') == 'high' or snapshot.get('latest_watch_event_type') == 'exit_consideration':
        reasons.append('watch_high_severity')
        return PositionLifecycleStatus.CLOSE, reasons, 'High-severity risk watch event indicates thesis deterioration and exit consideration.', Decimal('0.86')

    if edge <= Decimal('-0.04') or prediction_drift <= Decimal('-0.16') or unrealized_pnl <= Decimal('-180'):
        reasons.append('thesis_broken')
        return PositionLifecycleStatus.CLOSE, reasons, 'Prediction edge/probability drift and loss profile indicate thesis is likely broken.', Decimal('0.83')

    if edge < Decimal('0.01') or prediction_drift < Decimal('-0.06') or narrative_drift >= Decimal('0.55'):
        reasons.append('partial_deterioration')
        return PositionLifecycleStatus.REDUCE, reasons, 'Partial deterioration detected; reduce exposure while preserving optionality.', Decimal('0.72')

    if confidence < Decimal('0.40'):
        reasons.append('confidence_deterioration')
        return PositionLifecycleStatus.BLOCK_ADD, reasons, 'Prediction confidence is weak; block additional exposure and maintain watch.', Decimal('0.68')

    reasons.append('thesis_valid')
    return PositionLifecycleStatus.HOLD, reasons, 'Position remains aligned with current prediction/risk context and no severe watch events.', Decimal('0.74')
