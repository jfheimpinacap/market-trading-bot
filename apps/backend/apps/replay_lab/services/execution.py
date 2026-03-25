from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal

from django.utils.text import slugify

from apps.paper_trading.models import PaperAccount
from apps.paper_trading.services.portfolio import create_portfolio_snapshot
from apps.paper_trading.services.valuation import quantize_money


def create_replay_account(*, replay_run_id: int) -> PaperAccount:
    seed_balance = Decimal('10000.00')
    name = f'Replay Account Run {replay_run_id}'
    return PaperAccount.objects.create(
        name=name,
        slug=slugify(f'replay-run-{replay_run_id}'),
        currency='USD',
        initial_balance=seed_balance,
        cash_balance=seed_balance,
        equity=seed_balance,
        notes='Isolated paper account for historical replay only.',
        is_active=False,
    )


@contextmanager
def activate_replay_account(account: PaperAccount):
    original_active = list(PaperAccount.objects.filter(is_active=True).values_list('id', flat=True))
    PaperAccount.objects.exclude(id=account.id).update(is_active=False)
    PaperAccount.objects.filter(id=account.id).update(is_active=True)
    try:
        yield
    finally:
        PaperAccount.objects.filter(id=account.id).update(is_active=False)
        if original_active:
            PaperAccount.objects.filter(id__in=original_active).update(is_active=True)


def snapshot_replay_account(account: PaperAccount, *, metadata: dict | None = None) -> None:
    create_portfolio_snapshot(account=account)
    if metadata:
        latest = account.snapshots.order_by('-captured_at', '-id').first()
        if latest:
            latest.metadata = {**latest.metadata, **metadata}
            latest.save(update_fields=['metadata', 'updated_at'])


def summarize_account(account: PaperAccount) -> tuple[Decimal, Decimal]:
    return quantize_money(account.total_pnl), quantize_money(account.equity)
