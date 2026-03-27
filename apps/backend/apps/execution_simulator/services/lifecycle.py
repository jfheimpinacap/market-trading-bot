from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.execution_simulator.models import (
    PaperExecutionAttemptStatus,
    PaperOrder,
    PaperOrderLifecycleRun,
    PaperOrderStatus,
)
from apps.execution_simulator.services.fills import create_attempt_and_fill, simulate_fill
from apps.execution_simulator.services.policies import get_policy
from apps.execution_simulator.services.portfolio_apply import apply_fill_to_portfolio


@transaction.atomic
def run_execution_lifecycle(*, open_only: bool = True, metadata: dict | None = None) -> PaperOrderLifecycleRun:
    metadata = metadata or {}
    run = PaperOrderLifecycleRun.objects.create(started_at=timezone.now(), metadata=metadata)

    queryset = PaperOrder.objects.select_related('market', 'paper_account').prefetch_related('attempts', 'fills')
    if open_only:
        queryset = queryset.filter(status__in=[PaperOrderStatus.OPEN, PaperOrderStatus.PARTIALLY_FILLED])

    orders = list(queryset.order_by('created_at', 'id')[:200])
    run.orders_reviewed = len(orders)

    for order in orders:
        policy = get_policy((order.metadata or {}).get('policy_profile'))
        result = simulate_fill(order, policy)
        _, fill = create_attempt_and_fill(order=order, result=result)

        if result.status == PaperExecutionAttemptStatus.CANCELLED:
            order.status = PaperOrderStatus.CANCELLED
            run.orders_cancelled += 1
        elif result.status == PaperExecutionAttemptStatus.EXPIRED:
            order.status = PaperOrderStatus.EXPIRED
            run.orders_expired += 1
        elif result.status == PaperExecutionAttemptStatus.NO_FILL:
            run.no_fill_attempts += 1
            if order.status == PaperOrderStatus.OPEN:
                run.orders_open += 1
        elif fill:
            apply_fill_to_portfolio(order=order, fill_quantity=fill.fill_quantity, fill_price=fill.fill_price)
            order.remaining_quantity = (order.remaining_quantity - fill.fill_quantity).quantize(Decimal('0.0000'))
            if order.remaining_quantity <= Decimal('0'):
                order.remaining_quantity = Decimal('0.0000')
                order.status = PaperOrderStatus.FILLED
                order.effective_price = fill.fill_price
                run.orders_filled += 1
            else:
                order.status = PaperOrderStatus.PARTIALLY_FILLED
                order.effective_price = fill.fill_price
                run.orders_partial += 1

        order.save(update_fields=['wait_cycles', 'remaining_quantity', 'status', 'effective_price', 'updated_at'])

    run.finished_at = timezone.now()
    run.summary = (
        f'Execution lifecycle run reviewed={run.orders_reviewed}, filled={run.orders_filled}, partial={run.orders_partial}, '
        f'open={run.orders_open}, cancelled={run.orders_cancelled}, expired={run.orders_expired}, no_fill={run.no_fill_attempts}.'
    )
    run.save()
    return run
