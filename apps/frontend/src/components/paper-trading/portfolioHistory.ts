import type { PaperPortfolioHistoryPoint, PaperPortfolioSnapshot } from '../../types/paperTrading';

function parsePaperNumber(value: string | null) {
  if (value === null || value === '') {
    return null;
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

export function mapSnapshotsToPortfolioHistoryPoints(
  snapshots: PaperPortfolioSnapshot[],
): PaperPortfolioHistoryPoint[] {
  return [...snapshots]
    .sort((left, right) => new Date(left.captured_at).getTime() - new Date(right.captured_at).getTime())
    .map((snapshot) => ({
      id: snapshot.id,
      capturedAt: snapshot.captured_at,
      capturedAtLabel: new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(snapshot.captured_at)),
      cashBalance: parsePaperNumber(snapshot.cash_balance),
      equity: parsePaperNumber(snapshot.equity),
      realizedPnl: parsePaperNumber(snapshot.realized_pnl),
      unrealizedPnl: parsePaperNumber(snapshot.unrealized_pnl),
      totalPnl: parsePaperNumber(snapshot.total_pnl),
      openPositionsCount: snapshot.open_positions_count,
    }));
}

export function hasPortfolioHistorySeries(
  points: PaperPortfolioHistoryPoint[],
  key: 'equity' | 'cashBalance' | 'totalPnl',
) {
  return points.some((point) => point[key] !== null);
}

export function getPortfolioHistoryValueRange(points: PaperPortfolioHistoryPoint[]) {
  const values = points.flatMap((point) => [point.equity, point.cashBalance, point.totalPnl])
    .filter((value): value is number => value !== null);

  if (values.length === 0) {
    return null;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);

  if (min === max) {
    const padding = Math.max(Math.abs(max) * 0.08, 1);
    return { min: min - padding, max: max + padding };
  }

  const padding = Math.max((max - min) * 0.12, 1);
  return {
    min: min - padding,
    max: max + padding,
  };
}
