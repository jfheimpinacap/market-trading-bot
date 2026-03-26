from __future__ import annotations

from decimal import Decimal

from apps.position_manager.models import PositionLifecycleStatus


def build_exit_plan(*, position, action: str, reason_codes: list[str], runtime_caps: dict, safety: dict) -> dict:
    quantity = Decimal(str(position.quantity))
    target_quantity = quantity
    execution_path = 'record_only'

    if action == PositionLifecycleStatus.CLOSE:
        target_quantity = Decimal('0')
    elif action == PositionLifecycleStatus.REDUCE:
        target_quantity = (quantity * Decimal('0.5000')).quantize(Decimal('0.0001'))

    quantity_delta = (quantity - target_quantity).quantize(Decimal('0.0001'))
    requires_operator = bool(runtime_caps.get('require_operator_for_all_trades'))
    safety_blocked = bool(runtime_caps.get('blocked_reasons')) or safety.get('hard_stop_active') or safety.get('kill_switch_enabled')

    auto_allowed = action in {PositionLifecycleStatus.CLOSE, PositionLifecycleStatus.REDUCE} and quantity_delta > 0 and bool(runtime_caps.get('allow_auto_execution')) and not requires_operator and not safety_blocked
    queue_required = action == PositionLifecycleStatus.REVIEW_REQUIRED or (action in {PositionLifecycleStatus.CLOSE, PositionLifecycleStatus.REDUCE} and not auto_allowed)

    if auto_allowed:
        execution_path = 'paper_auto_execute'
    elif queue_required:
        execution_path = 'operator_queue'

    final_action = PositionLifecycleStatus.REVIEW_REQUIRED if queue_required and action != PositionLifecycleStatus.HOLD else action

    return {
        'action': action,
        'target_quantity': target_quantity,
        'quantity_delta': quantity_delta,
        'execution_mode': 'paper_only',
        'queue_required': queue_required,
        'auto_execute_allowed': auto_allowed,
        'final_recommended_action': final_action,
        'execution_path': execution_path,
        'explanation': f'Runtime mode={runtime_caps.get("mode")}; safety={safety.get("status")}; reasons={", ".join(reason_codes)}',
    }
