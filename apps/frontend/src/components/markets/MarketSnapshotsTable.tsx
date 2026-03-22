import { SectionCard } from '../SectionCard';
import type { MarketSnapshot } from '../../types/markets';
import { formatCompactCurrency, formatDateTime, formatPercent } from './utils';

type MarketSnapshotsTableProps = {
  snapshots: MarketSnapshot[];
};

export function MarketSnapshotsTable({ snapshots }: MarketSnapshotsTableProps) {
  return (
    <SectionCard
      eyebrow="Snapshots"
      title="Recent market snapshots"
      description="Latest five observations returned by the backend detail endpoint for quick inspection."
    >
      {snapshots.length > 0 ? (
        <div className="markets-table-wrapper">
          <table className="markets-table markets-table--compact">
            <thead>
              <tr>
                <th>Captured at</th>
                <th>Probability</th>
                <th>Yes</th>
                <th>No</th>
                <th>Liquidity</th>
                <th>Volume</th>
              </tr>
            </thead>
            <tbody>
              {snapshots.map((snapshot) => (
                <tr key={snapshot.id}>
                  <td>{formatDateTime(snapshot.captured_at)}</td>
                  <td>{formatPercent(snapshot.market_probability)}</td>
                  <td>{formatPercent(snapshot.yes_price)}</td>
                  <td>{formatPercent(snapshot.no_price)}</td>
                  <td>{formatCompactCurrency(snapshot.liquidity)}</td>
                  <td>{formatCompactCurrency(snapshot.volume)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted-text">No recent snapshots were available for this market.</p>
      )}
    </SectionCard>
  );
}
