import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { PaperPosition } from '../../types/paperTrading';
import { PaperStatusBadge } from './PaperStatusBadge';
import { PnlBadge } from './PnlBadge';
import { SideBadge } from './SideBadge';
import { formatPaperCurrency, formatQuantity, formatTechnicalTimestamp } from './utils';

type PaperPositionsTableProps = {
  positions: PaperPosition[];
  currency: string;
};

export function PaperPositionsTable({ positions, currency }: PaperPositionsTableProps) {
  function handleMarketClick(event: MouseEvent<HTMLAnchorElement>, marketId: number) {
    event.preventDefault();
    navigate(`/markets/${marketId}`);
  }

  return (
    <div className="markets-table-wrapper">
      <table className="markets-table paper-table">
        <thead>
          <tr>
            <th>Market</th>
            <th>Side</th>
            <th>Quantity</th>
            <th>Avg entry</th>
            <th>Current mark</th>
            <th>Market value</th>
            <th>Unrealized PnL</th>
            <th>Realized PnL</th>
            <th>Status</th>
            <th>Last marked</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr key={position.id}>
              <td>
                <a href={`/markets/${position.market}`} className="market-link" onClick={(event) => handleMarketClick(event, position.market)}>
                  <strong>{position.market_title}</strong>
                  <span>Market #{position.market}</span>
                </a>
              </td>
              <td>
                <SideBadge side={position.side} />
              </td>
              <td>{formatQuantity(position.quantity)}</td>
              <td>{formatPaperCurrency(position.average_entry_price, currency)}</td>
              <td>{formatPaperCurrency(position.current_mark_price, currency)}</td>
              <td>{formatPaperCurrency(position.market_value, currency)}</td>
              <td>
                <PnlBadge value={position.unrealized_pnl}>{formatPaperCurrency(position.unrealized_pnl, currency)}</PnlBadge>
              </td>
              <td>
                <PnlBadge value={position.realized_pnl}>{formatPaperCurrency(position.realized_pnl, currency)}</PnlBadge>
              </td>
              <td>
                <div className="paper-table__status-stack">
                  <PaperStatusBadge value={position.status} />
                  <span className="muted-text">{position.market_status}</span>
                </div>
              </td>
              <td>{formatTechnicalTimestamp(position.last_marked_at ?? position.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
