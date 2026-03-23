import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { TradeReviewDetail } from '../../types/reviews';
import { RiskDecisionBadge } from '../markets/RiskDecisionBadge';
import { formatDateTime, formatPercent, titleize } from '../markets/utils';
import { formatPaperCurrency, formatQuantity } from '../paper-trading/utils';
import { ReviewOutcomeBadge } from './ReviewOutcomeBadge';

type ReviewDetailPanelProps = {
  review: TradeReviewDetail;
};

function renderSignalContextEntry(value: Record<string, unknown>, index: number) {
  const headline = String(value.headline ?? 'Demo signal');
  const direction = titleize(String(value.direction ?? 'neutral'));
  const actionable = value.is_actionable ? 'Actionable' : 'Not actionable';
  const score = value.score ? `Score ${String(value.score)}` : null;
  const confidence = value.confidence ? `Confidence ${Math.round(Number(value.confidence) * 100)}%` : null;

  return (
    <li key={`${value.signal_id ?? index}`}>
      <strong>{headline}</strong>
      <span>{direction} · {actionable}</span>
      {score || confidence ? <span>{[score, confidence].filter(Boolean).join(' · ')}</span> : null}
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
            Review for trade #{review.trade_id} in account {review.paper_account_slug}. Generated from local-only demo heuristics and linked back into market detail and portfolio.
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
          <p className="section-label">Trade and market context</p>
          <dl className="dashboard-key-value-list">
            <div><dt>Trade</dt><dd>{titleize(review.trade_type)} {review.trade_side}</dd></div>
            <div><dt>Market</dt><dd>{review.market_title}</dd></div>
            <div><dt>Market status</dt><dd>{titleize(review.market_status)}</dd></div>
            <div><dt>Risk at trade time</dt><dd><RiskDecisionBadge decision={review.risk_decision_at_trade} /></dd></div>
            <div><dt>Probability at trade</dt><dd>{formatPercent(review.market_probability_at_trade)}</dd></div>
            <div><dt>Probability now</dt><dd>{formatPercent(review.market_probability_now)}</dd></div>
          </dl>
        </article>
        <article className="panel">
          <p className="section-label">Summary and learning</p>
          <p><strong>Summary:</strong> {review.summary}</p>
          <p><strong>Rationale:</strong> {review.rationale}</p>
          <p><strong>Lesson:</strong> {review.lesson || 'No lesson generated.'}</p>
          <p><strong>Recommendation:</strong> {review.recommendation || 'No recommendation generated.'}</p>
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
                <span>Return to the market, inspect the latest signals, and compare with the original trade context.</span>
              </a>
            </li>
            <li>
              <a href="/portfolio" className="market-link" onClick={(event) => handleNavigate(event, '/portfolio')}>
                <strong>Open portfolio</strong>
                <span>Check the current account state, trade history, and equity impact related to this review.</span>
              </a>
            </li>
            <li>
              <a href="/postmortem" className="market-link" onClick={(event) => handleNavigate(event, '/postmortem')}>
                <strong>Return to post-mortem queue</strong>
                <span>Go back to the review tray and compare this outcome with other trades.</span>
              </a>
            </li>
          </ul>
        </article>
      </div>
    </section>
  );
}
