from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.paper_trading.models import PaperPortfolioSnapshot, PaperPosition, PaperPositionStatus
from apps.paper_trading.services.portfolio import get_active_account


def _to_float(value: Decimal | int | float | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _build_bucket(rows, label_key: str, exposure_total: Decimal) -> list[dict]:
    items: list[dict] = []
    total = _to_float(exposure_total)
    for row in rows:
        exposure = _to_float(row.get('exposure'))
        ratio = exposure / total if total > 0 else 0.0
        items.append({'label': row.get(label_key) or 'unknown', 'exposure': exposure, 'ratio': ratio})
    return sorted(items, key=lambda item: item['exposure'], reverse=True)


def build_exposure_snapshot_payload() -> dict:
    account = get_active_account()
    positions = PaperPosition.objects.filter(account=account, status=PaperPositionStatus.OPEN, quantity__gt=0).select_related('market__provider')
    total_exposure = positions.aggregate(total=Sum('market_value')).get('total') or Decimal('0')

    by_market = positions.values('market__slug').annotate(exposure=Sum('market_value'))
    by_provider = positions.values('market__provider__slug').annotate(exposure=Sum('market_value'))
    by_category = positions.values('market__category').annotate(exposure=Sum('market_value'))

    exposure_by_market = _build_bucket(by_market, 'market__slug', total_exposure)
    exposure_by_provider = _build_bucket(by_provider, 'market__provider__slug', total_exposure)
    exposure_by_category = _build_bucket(by_category, 'market__category', total_exposure)

    market_ratio = exposure_by_market[0]['ratio'] if exposure_by_market else 0.0
    provider_ratio = exposure_by_provider[0]['ratio'] if exposure_by_provider else 0.0

    recent_snapshots = list(PaperPortfolioSnapshot.objects.filter(account=account).order_by('-captured_at', '-id')[:20])
    peak_equity = max([account.equity, *[snap.equity for snap in recent_snapshots]]) if recent_snapshots else account.equity
    drawdown_pct = float((peak_equity - account.equity) / peak_equity) if peak_equity > 0 else 0.0

    reserve_ratio = float(account.cash_balance / account.equity) if account.equity > 0 else 0.0

    return {
        'total_equity': account.equity,
        'available_cash': account.cash_balance,
        'total_exposure': total_exposure,
        'open_positions': positions.count(),
        'unrealized_pnl': account.unrealized_pnl,
        'recent_drawdown_pct': drawdown_pct,
        'cash_reserve_ratio': reserve_ratio,
        'concentration_market_ratio': market_ratio,
        'concentration_provider_ratio': provider_ratio,
        'exposure_by_market': exposure_by_market,
        'exposure_by_provider': exposure_by_provider,
        'exposure_by_category': exposure_by_category,
    }
