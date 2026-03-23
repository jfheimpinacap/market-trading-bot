import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { PaperTrade } from '../../types/paperTrading';
import type { TradeReview } from '../../types/reviews';
import { PaperStatusBadge } from './PaperStatusBadge';
import { SideBadge } from './SideBadge';
import { formatPaperCurrency, formatQuantity, formatTechnicalTimestamp } from './utils';
import { titleize } from '../markets/utils';
import { ReviewOutcomeBadge } from '../postmortem/ReviewOutcomeBadge';

type PaperTradesTableProps = {
  trades: PaperTrade[];
  currency: string;
  reviewLookup?: Record<number, TradeReview>;
};

export function PaperTradesTable({ trades, currency, reviewLookup = {} }: PaperTradesTableProps) {
  function handleNavigate(event: MouseEvent<HTMLAnchorElement>, path: string) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(path);
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
            <th>Review</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => {
            const review = reviewLookup[trade.id];

            return (
              <tr key={trade.id}>
                <td>{formatTechnicalTimestamp(trade.executed_at)}</td>
                <td>
                  <a href={`/markets/${trade.market}`} className="market-link" onClick={(event) => handleNavigate(event, `/markets/${trade.market}`)}>
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
                <td>
                  {review ? (
                    <a href={`/postmortem/${review.id}`} className="market-link" onClick={(event) => handleNavigate(event, `/postmortem/${review.id}`)}>
                      <strong><ReviewOutcomeBadge outcome={review.outcome} status={review.review_status} /></strong>
                      <span>Score {review.score} · Open review</span>
                    </a>
                  ) : (
                    <span className="paper-inline-muted">No review yet</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
