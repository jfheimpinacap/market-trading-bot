import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { TradeReview } from '../../types/reviews';
import { formatDateTime, formatNumber, titleize } from '../markets/utils';
import { formatPaperCurrency, formatQuantity } from '../paper-trading/utils';
import { ReviewOutcomeBadge } from './ReviewOutcomeBadge';

type TradeReviewsTableProps = {
  reviews: TradeReview[];
};

export function TradeReviewsTable({ reviews }: TradeReviewsTableProps) {
  function handleNavigate(event: MouseEvent<HTMLAnchorElement>, path: string) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(path);
  }

  return (
    <div className="markets-table-wrapper">
      <table className="markets-table paper-table postmortem-table">
        <thead>
          <tr>
            <th>Reviewed at</th>
            <th>Trade</th>
            <th>Market</th>
            <th>Outcome</th>
            <th>Score</th>
            <th>Price delta</th>
            <th>Summary</th>
            <th>Recommendation</th>
          </tr>
        </thead>
        <tbody>
          {reviews.map((review) => (
            <tr key={review.id}>
              <td>{formatDateTime(review.reviewed_at)}</td>
              <td>
                <a href={`/postmortem/${review.id}`} className="market-link" onClick={(event) => handleNavigate(event, `/postmortem/${review.id}`)}>
                  <strong>{titleize(review.trade_type)} {review.trade_side}</strong>
                  <span>Trade #{review.trade_id} · Qty {formatQuantity(review.trade_quantity)}</span>
                </a>
              </td>
              <td>
                <a href={`/markets/${review.market}`} className="market-link" onClick={(event) => handleNavigate(event, `/markets/${review.market}`)}>
                  <strong>{review.market_title}</strong>
                  <span>{titleize(review.market_status)}</span>
                </a>
              </td>
              <td>
                <ReviewOutcomeBadge outcome={review.outcome} status={review.review_status} />
              </td>
              <td>{formatNumber(review.score)}</td>
              <td>{review.price_delta ? formatPaperCurrency(review.price_delta, 'USD') : '—'}</td>
              <td>
                <div className="postmortem-cell-copy">
                  <strong>{review.summary}</strong>
                  <span>{review.lesson || 'No lesson captured yet.'}</span>
                </div>
              </td>
              <td>{review.recommendation || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
