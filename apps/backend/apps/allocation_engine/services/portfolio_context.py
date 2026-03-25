from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from apps.paper_trading.models import PaperAccount, PaperPosition, PaperPositionStatus


@dataclass
class PortfolioContext:
    account: PaperAccount
    cash_balance: Decimal
    reserve_cash_amount: Decimal
    available_cash: Decimal
    total_exposure_value: Decimal
    market_exposure: dict[int, Decimal]



def build_portfolio_context(*, account: PaperAccount, reserve_cash_amount: Decimal) -> PortfolioContext:
    open_positions = PaperPosition.objects.filter(account=account, status=PaperPositionStatus.OPEN)
    total_exposure = open_positions.aggregate(total=Sum('market_value')).get('total') or Decimal('0.00')

    market_exposure: dict[int, Decimal] = {}
    for row in open_positions.values('market_id').annotate(total=Sum('market_value')):
        market_exposure[row['market_id']] = row['total'] or Decimal('0.00')

    available_cash = max(Decimal('0.00'), account.cash_balance - reserve_cash_amount)
    return PortfolioContext(
        account=account,
        cash_balance=account.cash_balance,
        reserve_cash_amount=reserve_cash_amount,
        available_cash=available_cash,
        total_exposure_value=total_exposure,
        market_exposure=market_exposure,
    )
