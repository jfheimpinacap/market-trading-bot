import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { TradeReviewDetail } from '../../types/reviews';
import { formatDateTime, formatPercent, titleize } from '../markets/utils';
import { formatPaperCurrency, formatQuantity } from '../paper-trading/utils';
import { ReviewOutcomeBadge } from './ReviewOutcomeBadge';

type ReviewDetailPanelProps = {
  review: TradeReviewDetail;
};

function renderSignalContextEntry(value: Record<string, unknown>, index: number) {
  return (
    <li key={`${value.signal_id ?? index}`}>
      <strong>{String(value.headline ?? 'Demo signal')}</strong>
      <span>
        {titleize(String(value.direction ?? 'neutral'))}
        {' · '}
        {value.is_actionable ? 'Actionable' : 'Monitor only'}
      </span>
    </li>
  );
}

export function ReviewDetailPanel({ review }: ReviewDetailPanelProps) {
  function handleNavigate(event: MouseEvent<HTMLAnchorElement>, path: string) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(path);
  }

  return (
    <section className="panel postmortem-detail-panel">
      <div className="postmortem-detail-panel__header">
        <div>
          <p className="section-label">Trade review detail</p>
          <h2>{review.market_title}</h2>
          <p>
            Review for trade #{review.trade_id} in account {review.paper_account_slug}. Generated from local-only demo heuristics.
          </p>
        </div>
        <ReviewOutcomeBadge outcome={review.outcome} status={review.review_status} />
      </div>

      <div className="content-grid content-grid--three-columns">
        <article className="panel postmortem-detail-metric">
          <span>Trade setup</span>
          <strong>{titleize(review.trade_type)} {review.trade_side}</strong>
          <p>Quantity {formatQuantity(review.trade_quantity)} · Executed {formatDateTime(review.trade_executed_at)}</p>
        </article>
        <article className="panel postmortem-detail-metric">
          <span>Price move</span>
          <strong>{formatPaperCurrency(review.price_delta, 'USD')}</strong>
          <p>Entry {formatPaperCurrency(review.entry_price, 'USD')} → Current {formatPaperCurrency(review.current_market_price, 'USD')}</p>
        </article>
        <article className="panel postmortem-detail-metric">
          <span>Estimated PnL</span>
          <strong>{formatPaperCurrency(review.pnl_estimate, 'USD')}</strong>
          <p>Score {review.score}/100 · Confidence {formatPercent(review.confidence)}</p>
        </article>
      </div>

      <div className="content-grid content-grid--two-columns">
        <article className="panel">
          <p className="section-label">Summary</p>
          <p>{review.summary}</p>
          <p className="section-label">Rationale</p>
          <p>{review.rationale}</p>
        </article>
        <article className="panel">
          <p className="section-label">Lessons and next step</p>
          <p><strong>Lesson:</strong> {review.lesson || 'No lesson generated.'}</p>
          <p><strong>Recommendation:</strong> {review.recommendation || 'No recommendation generated.'}</p>
          <p><strong>Risk at trade time:</strong> {review.risk_decision_at_trade ? titleize(review.risk_decision_at_trade) : 'Not captured'}</p>
          <p><strong>Reviewed at:</strong> {formatDateTime(review.reviewed_at)}</p>
        </article>
      </div>

      <div className="content-grid content-grid--two-columns">
        <article className="panel">
          <p className="section-label">Signal context</p>
          {review.signals_context.length > 0 ? (
            <ul className="postmortem-detail-list">
              {review.signals_context.map((entry, index) => renderSignalContextEntry(entry, index))}
            </ul>
          ) : (
            <p>No signal context was attached to this review.</p>
          )}
        </article>
        <article className="panel">
          <p className="section-label">Linked navigation</p>
          <ul className="postmortem-detail-list">
            <li>
              <a href={`/markets/${review.market}`} className="market-link" onClick={(event) => handleNavigate(event, `/markets/${review.market}`)}>
                <strong>Open market detail</strong>
                <span>Inspect the current market status and snapshot history.</span>
              </a>
            </li>
            <li>
              <a href="/portfolio" className="market-link" onClick={(event) => handleNavigate(event, '/portfolio')}>
                <strong>Open portfolio</strong>
                <span>Compare this review with the current paper trading history.</span>
              </a>
            </li>
            <li>
              <a href="/postmortem" className="market-link" onClick={(event) => handleNavigate(event, '/postmortem')}>
                <strong>Return to post-mortem queue</strong>
                <span>Go back to the review tray and inspect more trades.</span>
              </a>
            </li>
          </ul>
        </article>
      </div>
    </section>
  );
}
