import type { MarketHistoryPoint, MarketSnapshot } from '../../types/markets';

function parseNullableNumber(value: string | null): number | null {
  if (value === null || value === '') {
    return null;
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

export function mapSnapshotsToMarketHistoryPoints(snapshots: MarketSnapshot[]): MarketHistoryPoint[] {
  return [...snapshots]
    .sort((left, right) => new Date(left.captured_at).getTime() - new Date(right.captured_at).getTime())
    .map((snapshot) => ({
      id: snapshot.id,
      capturedAt: snapshot.captured_at,
      capturedAtLabel: new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(snapshot.captured_at)),
      marketProbability: parseNullableNumber(snapshot.market_probability),
      yesPrice: parseNullableNumber(snapshot.yes_price),
      noPrice: parseNullableNumber(snapshot.no_price),
      liquidity: parseNullableNumber(snapshot.liquidity),
    }));
}

export function hasHistorySeries(points: MarketHistoryPoint[], key: 'marketProbability' | 'yesPrice' | 'noPrice') {
  return points.some((point) => point[key] !== null);
}
