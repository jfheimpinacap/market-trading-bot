import { titleize } from './utils';

type MarketStatusBadgeProps = {
  status: string;
};

export function MarketStatusBadge({ status }: MarketStatusBadgeProps) {
  const normalizedStatus = status.toLowerCase();

  return <span className={`market-badge market-badge--status market-badge--${normalizedStatus}`}>{titleize(status)}</span>;
}
