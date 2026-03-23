from decimal import Decimal

from django.db import transaction

from apps.paper_trading.models import PaperAccount, PaperPortfolioSnapshot, PaperPositionStatus
from apps.paper_trading.services.valuation import quantize_money, revalue_account

DEFAULT_ACCOUNT_SLUG = 'demo-paper-account'
DEFAULT_ACCOUNT_NAME = 'Demo Paper Account'
DEFAULT_INITIAL_BALANCE = Decimal('10000.00')


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
