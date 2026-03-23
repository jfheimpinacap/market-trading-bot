import { formatDateTime, formatNumber } from '../markets/utils';
import type { TradeReviewSummary } from '../../types/reviews';

type PostMortemSummaryCardsProps = {
  summary: TradeReviewSummary;
};

const cards = [
  { key: 'total_reviews', label: 'Total reviews', helper: 'Generated trade reviews currently available in the demo workspace.' },
  { key: 'favorable_reviews', label: 'Favorable', helper: 'Trades that improved after execution under the current heuristic.' },
  { key: 'neutral_reviews', label: 'Neutral', helper: 'Trades that barely moved after execution.' },
  { key: 'unfavorable_reviews', label: 'Unfavorable', helper: 'Trades that moved against the executed side.' },
  { key: 'stale_reviews', label: 'Stale', helper: 'Existing reviews that should be refreshed because the market changed later.' },
] as const;

export function PostMortemSummaryCards({ summary }: PostMortemSummaryCardsProps) {
  return (
    <div className="content-grid content-grid--three-columns">
      {cards.map((card) => (
        <article key={card.key} className="panel postmortem-stat-card">
          <span>{card.label}</span>
          <strong>{formatNumber(summary[card.key])}</strong>
          <p>{card.helper}</p>
        </article>
      ))}
      <article className="panel postmortem-stat-card">
        <span>Average score</span>
        <strong>{summary.average_score ? `${summary.average_score}/100` : '—'}</strong>
        <p>Simple demo score from the local heuristic rules.</p>
      </article>
      <article className="panel postmortem-stat-card">
        <span>Latest review</span>
        <strong>{formatDateTime(summary.latest_reviewed_at)}</strong>
        <p>Most recent review refresh captured by the backend.</p>
      </article>
    </div>
  );
}
