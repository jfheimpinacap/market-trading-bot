from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.paper_trading.models import PaperAccount, PaperPortfolioSnapshot, PaperPositionStatus
from apps.paper_trading.services.valuation import quantize_money, revalue_account

DEFAULT_ACCOUNT_SLUG = 'demo-paper-account'
DEFAULT_ACCOUNT_NAME = 'Demo Paper Account'
DEFAULT_INITIAL_BALANCE = Decimal('10000.00')
SUMMARY_STATUS_OK = 'PAPER_ACCOUNT_SUMMARY_OK'
SUMMARY_STATUS_DEGRADED = 'PAPER_ACCOUNT_SUMMARY_DEGRADED'
SUMMARY_STATUS_UNAVAILABLE = 'PAPER_ACCOUNT_SUMMARY_UNAVAILABLE'

REASON_FIELD_FALLBACK_USED = 'PAPER_ACCOUNT_FIELD_FALLBACK_USED'
REASON_FIELD_MISSING = 'PAPER_ACCOUNT_FIELD_MISSING'


@transaction.atomic
def ensure_demo_account(*, initial_balance: Decimal = DEFAULT_INITIAL_BALANCE) -> tuple[PaperAccount, bool]:
    account, created = PaperAccount.objects.get_or_create(
        slug=DEFAULT_ACCOUNT_SLUG,
        defaults={
            'name': DEFAULT_ACCOUNT_NAME,
            'currency': 'USD',
            'initial_balance': quantize_money(initial_balance),
            'cash_balance': quantize_money(initial_balance),
            'equity': quantize_money(initial_balance),
            'notes': 'Local-first paper trading account for demo portfolio flows.',
            'is_active': True,
        },
    )
    if account.is_active is False:
        account.is_active = True
        account.save(update_fields=['is_active', 'updated_at'])
    return account, created


def get_active_account() -> PaperAccount:
    account = PaperAccount.objects.filter(is_active=True).order_by('id').first()
    if account:
        return account
    account, _ = ensure_demo_account()
    return account


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return quantize_money(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _resolve_field(account: PaperAccount, primary: str, alternates: tuple[str, ...]) -> tuple[Decimal | None, str | None]:
    value = _to_decimal(getattr(account, primary, None))
    if value is not None:
        return value, None
    for name in alternates:
        fallback = _to_decimal(getattr(account, name, None))
        if fallback is not None:
            return fallback, REASON_FIELD_FALLBACK_USED
    return None, REASON_FIELD_MISSING


def build_account_financial_summary(*, account: PaperAccount) -> dict:
    """
    Resolve account balances defensively across minor schema/property differences.
    """
    reasons: list[str] = []
    status = SUMMARY_STATUS_OK

    cash, cash_reason = _resolve_field(account, 'cash_balance', ('cash',))
    realized, realized_reason = _resolve_field(account, 'realized_pnl', ('realized',))
    unrealized, unrealized_reason = _resolve_field(account, 'unrealized_pnl', ('unrealized',))
    equity, equity_reason = _resolve_field(account, 'equity', ('equity_value', 'portfolio_value'))

    for reason in (cash_reason, realized_reason, unrealized_reason, equity_reason):
        if reason:
            reasons.append(reason)

    if equity is None and cash is not None:
        total_market_value = Decimal('0.00')
        for position in account.positions.all():
            total_market_value += _to_decimal(getattr(position, 'market_value', None)) or Decimal('0.00')
        equity = quantize_money(cash + total_market_value)
        reasons.append(REASON_FIELD_FALLBACK_USED)

    unique_reasons = list(dict.fromkeys(reasons))
    if unique_reasons:
        status = SUMMARY_STATUS_DEGRADED
    if cash is None and equity is None and realized is None and unrealized is None:
        status = SUMMARY_STATUS_UNAVAILABLE

    return {
        'cash': cash,
        'equity': equity,
        'realized_pnl': realized,
        'unrealized_pnl': unrealized,
        'summary_status': status,
        'reason_codes': unique_reasons,
    }


@transaction.atomic
def create_portfolio_snapshot(*, account: PaperAccount, open_positions_count: int | None = None) -> PaperPortfolioSnapshot:
    if open_positions_count is None:
        open_positions_count = account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0).count()
    return PaperPortfolioSnapshot.objects.create(
        account=account,
        cash_balance=account.cash_balance,
        equity=account.equity,
        realized_pnl=account.realized_pnl,
        unrealized_pnl=account.unrealized_pnl,
        total_pnl=account.total_pnl,
        open_positions_count=open_positions_count,
        metadata={
            'positions': {
                'open_count': open_positions_count,
            },
        },
    )


def build_account_summary(*, account: PaperAccount) -> dict:
    revalue_account(account)
    positions = account.positions.select_related('market').order_by('-market_value', 'market__title')
    open_positions = [position for position in positions if position.status == PaperPositionStatus.OPEN and position.quantity > 0]
    exposure_by_market = [
        {
            'market_id': position.market_id,
            'market_title': position.market.title,
            'side': position.side,
            'quantity': position.quantity,
            'market_value': position.market_value,
            'unrealized_pnl': position.unrealized_pnl,
            'current_mark_price': position.current_mark_price,
        }
        for position in open_positions
    ]
    recent_trades = list(
        account.trades.select_related('market').order_by('-executed_at', '-id')[:10].values(
            'id',
            'market_id',
            'market__title',
            'trade_type',
            'side',
            'quantity',
            'price',
            'gross_amount',
            'status',
            'executed_at',
        )
    )
    return {
        'account': account,
        'open_positions_count': len(open_positions),
        'closed_positions_count': account.positions.filter(status=PaperPositionStatus.CLOSED).count(),
        'exposure_by_market': exposure_by_market,
        'recent_trades': recent_trades,
    }
