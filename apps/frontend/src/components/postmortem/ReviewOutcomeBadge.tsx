import { titleize } from '../markets/utils';
import type { TradeReviewOutcome, TradeReviewStatus } from '../../types/reviews';

type ReviewOutcomeBadgeProps = {
  outcome?: TradeReviewOutcome;
  status?: TradeReviewStatus;
};

export function ReviewOutcomeBadge({ outcome, status }: ReviewOutcomeBadgeProps) {
  const normalizedOutcome = (outcome ?? '').toUpperCase();
  const normalizedStatus = (status ?? '').toUpperCase();
  const tone = normalizedOutcome === 'FAVORABLE'
    ? 'favorable'
    : normalizedOutcome === 'UNFAVORABLE'
      ? 'unfavorable'
      : 'neutral';

  return (
    <span className={`review-outcome-badge review-outcome-badge--${tone}`}>
      {titleize(normalizedOutcome || 'Unknown')}
      {normalizedStatus === 'STALE' ? ' · Stale' : ''}
    </span>
  );
}
