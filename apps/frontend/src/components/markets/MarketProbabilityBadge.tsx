import { formatPercent } from './utils';

type MarketProbabilityBadgeProps = {
  value: string | null;
};

export function MarketProbabilityBadge({ value }: MarketProbabilityBadgeProps) {
  return <span className="market-probability-badge">{formatPercent(value)}</span>;
}
