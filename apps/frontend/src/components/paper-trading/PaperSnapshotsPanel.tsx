import type { PaperPortfolioSnapshot } from '../../types/paperTrading';
import { PnlBadge } from './PnlBadge';
import { formatPaperCurrency, formatTechnicalTimestamp } from './utils';

type PaperSnapshotsPanelProps = {
  snapshots: PaperPortfolioSnapshot[];
  currency: string;
};

export function PaperSnapshotsPanel({ snapshots, currency }: PaperSnapshotsPanelProps) {
  return (
    <div className="markets-table-wrapper">
      <table className="markets-table markets-table--compact paper-table">
        <thead>
          <tr>
            <th>Captured at</th>
            <th>Cash balance</th>
            <th>Equity</th>
            <th>Realized PnL</th>
            <th>Unrealized PnL</th>
            <th>Total PnL</th>
            <th>Open positions</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.map((snapshot) => (
            <tr key={snapshot.id}>
              <td>{formatTechnicalTimestamp(snapshot.captured_at)}</td>
              <td>{formatPaperCurrency(snapshot.cash_balance, currency)}</td>
              <td>{formatPaperCurrency(snapshot.equity, currency)}</td>
              <td>
                <PnlBadge value={snapshot.realized_pnl}>{formatPaperCurrency(snapshot.realized_pnl, currency)}</PnlBadge>
              </td>
              <td>
                <PnlBadge value={snapshot.unrealized_pnl}>{formatPaperCurrency(snapshot.unrealized_pnl, currency)}</PnlBadge>
              </td>
              <td>
                <PnlBadge value={snapshot.total_pnl}>{formatPaperCurrency(snapshot.total_pnl, currency)}</PnlBadge>
              </td>
              <td>{snapshot.open_positions_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
