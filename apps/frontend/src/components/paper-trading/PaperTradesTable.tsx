import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { PaperTrade } from '../../types/paperTrading';
import { PaperStatusBadge } from './PaperStatusBadge';
import { SideBadge } from './SideBadge';
import { formatPaperCurrency, formatQuantity, formatTechnicalTimestamp } from './utils';
import { titleize } from '../markets/utils';

type PaperTradesTableProps = {
  trades: PaperTrade[];
  currency: string;
};

export function PaperTradesTable({ trades, currency }: PaperTradesTableProps) {
  function handleMarketClick(event: MouseEvent<HTMLAnchorElement>, marketId: number) {
    event.preventDefault();
    navigate(`/markets/${marketId}`);
  }

  return (
    <div className="markets-table-wrapper">
      <table className="markets-table paper-table">
        <thead>
          <tr>
            <th>Executed at</th>
            <th>Market</th>
            <th>Trade type</th>
            <th>Side</th>
            <th>Quantity</th>
            <th>Price</th>
            <th>Gross amount</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <tr key={trade.id}>
              <td>{formatTechnicalTimestamp(trade.executed_at)}</td>
              <td>
                <a href={`/markets/${trade.market}`} className="market-link" onClick={(event) => handleMarketClick(event, trade.market)}>
                  <strong>{trade.market_title}</strong>
                  <span>Market #{trade.market}</span>
                </a>
              </td>
              <td>{titleize(trade.trade_type)}</td>
              <td>
                <SideBadge side={trade.side} />
              </td>
              <td>{formatQuantity(trade.quantity)}</td>
              <td>{formatPaperCurrency(trade.price, currency)}</td>
              <td>{formatPaperCurrency(trade.gross_amount, currency)}</td>
              <td>
                <PaperStatusBadge value={trade.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
